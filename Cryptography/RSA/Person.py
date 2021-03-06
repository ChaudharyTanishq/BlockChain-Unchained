from RSA import get_keys

class Person():
    def __init__(self, generate=True, debug=True, data=None):
        if debug:
            print(f"Generating Key Pair ... ", end="")
        
        if generate:
            self.public_key, self.private_key = get_keys()
        else:
            if data:    
                self.public_key = data['public_key']
                self.private_key = data['private_key']
            else:
                raise ValueError("Data must be input for generate = False")

        if debug:
            print(f"Done!")

    def encrypt(self, other_public_key, message):
        return pow(message, other_public_key['e'], other_public_key['n'])
    
    def decrypt(self, encrypted_message):
        return pow(encrypted_message, self.private_key['d'], self.public_key['n'])
