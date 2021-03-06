# Fixing Exploits

## 1. Fixing Underflow/Overflow
[SafeMath](https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/math/SafeMath.sol)

## 2. ReEntrancy

### The Exploit
Short Answer: Recursion 

Long Answer:
We deploy the contract ```Attack``` with the address of the ```SecureVault```. We now call the ```attack``` function, and send it ```1 wei```. This is deposited to the vault.

Now, we ask for the wei back. This we do by calling the ```withdraw``` function. The function now wants to send us the money back, but instead of letting it complete, in the ```fallback``` (the function which is called by ```withdraw```) function, we call the ```withdraw``` function again. This sends the function in a recursive loop, only stopping when there are ```1 wei``` left. We take the last wei as well :).

Its only after all of the calls are returned that one realises the damage done. 

#### a. Logical Fix

Change
```javascript
function withdraw(uint _amount) public {
    require(balances[msg.sender] >= _amount);
    
    (bool sent, ) = msg.sender.call{value: _amount}("");
    require(sent, "Failed to send Ether");
    
    // changing the balance only after the call is made; only when the transaction is successful
    balances[msg.sender] -= _amount;
}
```

to

```javascript
function withdraw(uint _amount) public {
    require(balances[msg.sender] >= _amount);
  
    // recalculating the balance regardless of the transaction's failure or success. It is not helpful for every case. Look for mutex locks, with the help of functional modifier.
    balances[msg.sender] -= _amount;
    
    (bool sent, ) = msg.sender.call{value: _amount}("");
    require(sent, "Failed to send Ether");  
}
```

#### b.Using Functional Modifier
```javascript
contract SecureVault{
    mapping(address => uint) public balances;
    bool internal locked;

    function deposit() public payable { balances[msg.sender] += msg.value; }

    // adding this modifer, which does not allow recursion
    modifier noReEntrancy(){
        require(!locked, "No Re-entrancy!")
        locked = true;
        _;
        locked = false;
    }

    function withdraw(uint _amount) public noReEntrancy {
        require(balances[msg.sender] >= _amount);
        
        (bool sent, ) = msg.sender.call{value: _amount}("");
        require(sent, "Failed to send Ether");
        
        // we now deduct the amount from the hacker, of course, only after the transaction's success.
        balances[msg.sender] -= _amount;
    }
    
    function getBalance() public view returns (uint) {
        return address(this).balance;
    }
}
```

## 3. Self Destruction

### The Attack
Short Answer: We take down everyone with us

Long Answer:

Quick Info: Self-destruct destroys the contract. It also has to remove any ether stored at the location, so it ends up transferring *all* the ether to the addess supplied, as, ```selfdestruct(transfer_address)```.

We can use this to force send ether to a contract, overriding all the conditions; doesn't matter if the function is non-payable, or there are input restrictions.

We now use this idea to send >=7 ethers, to a game of ```Gamble7```. This overrides the condition of 1 ether/deposition. However, this comes at the cost of the attacker not getting anything in return; there is no contract which the winning funds can be supplied to! (this can be bad incase there are other people who have put in 1 ether donations; they lose their money too)

### Fix
We relied on the internal ```address(this).balance```. The simple fix is to create our own ```uint public balance``` variable, storing the balance details here.

```javascript
contract Gamble7 {
    uint public target = 7 ether;
    
    // NOTE: Using private is also a mess; as is explored here.
    uint private balance;
    address public winner;
    
    function deposit() public payable {
        require(msg.value == 1 ether, "You have to spend exactly 1 ether!");

        // REPLACE
        // uint balance = address(this).balance;
        // WITH
        balance += msg.value;

        require(balance <= target, "The Game is Over");
        
        if(balance == target) winner = msg.sender;
    }
 
    function claimReward() public {
        require(msg.sender == winner, "You are not the winner");

        (bool sent, ) = msg.sender.call{value: address(this).balance}("");
        require(sent, "Failed to send Ether");
    }
}
```

## 4. Denial of Service

### The Attack
Short Answer: We refuse to accept the refund

Long Answer: The contract ```KinfOfEther``` allows only one king, who has maximum amount of ether in storage currently. The "kings" are usualy accounts of people, residing in the ```EVM```, along with contracts themselves. Infact what we exploit is partly the fact that user account and contract account addresses are indistinguishable; we can have a contract pretend to be a user. This is not an issue, and is perfectly valid. [Source](https://stackoverflow.com/questions/42081194/where-do-smart-contracts-reside-in-blockchain-ethereum-or-hyperledger)

Now, note how the contract ```Attack``` does not have any fallback function to accept the ether back. This simply means that the transactions will fail; this contract can *not* receive any ether. Thus, we stay the king, by not accepting the refund XD

### Fix
Do not auto-refund. Add a new function to withdraw the funds. This way execution will be un-haltered.


## 5. Phishing

### The attack
Short Answer: You trick someone into running your code

Long Answer: You trick someone into running your code.

### Fix
Change ```tx.origin``` with ```msg.sender```. Ezpz.

## 6. Hiding (Malicious) Code

### The attack
Short Answer: Evil Twin

Long Answer: Three contracts, with two visible (Let: A, B) and the other hidden (Let: C). C (The hidden one) is external, having malicious code. A is using an instance of B. B and C look similar; too similar infact. The variables to be accessed from A are already known, and the C contract knows this. It mirrors all; the function signatures, down to the variable sizes (names are irrelevant, look at this from a EVM point of view).

From the outside, it looks as if A is instantiating B. But, if we pass it the address of C, no one knows better.

```javascript
contract Foo {
    Bar bar;

    // we pass in the address; which can be of ... an external contract
    constructor(address _bar) public { bar = Bar(_bar); }
    function callBar() public { bar.log(); }
}

```

### The Fix
```javascript
contract Foo {
    Bar bar;

    // That's it! No address can be sneaked in :)
    constructor() public { bar = new Bar(); }
    function callBar() public { bar.log(); }
}

```

## 7. Honey Pot

### The attack
In this case, we trick the attacker into thinking that the ```SceureVault``` has a re-entrancy exploit.
We then trap the attacker into our honeypot, which is hidden away. 

Steps:
deploy ```HoneyPot```
deploy ```SceureVault``` with address of ```HoneyPot```
deploy ```Attack``` with address of ```SceureVault```
run the ```attack``` function inside of ```Attack```
get trapped

NOTE: The trap essentially reverts the state changed by the ```withdraw``` function. This means ether can be deposited into the vault, but not be taken out. So, is the money lost forever? No. We can add a self-destruct functionality, that can transfer the funds, to the required address.

### The Fix
As a hacker this time, you need to check the difference between:

```javascript 
bar = Bar(_bar);
// VERSUS
bar = new Bar();
```
