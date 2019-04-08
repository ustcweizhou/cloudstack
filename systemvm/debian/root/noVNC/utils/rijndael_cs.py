import rijndael
import base64
import python_Rijndael

KEY_SIZE = 16
IV_SIZE = 16
BLOCK_SIZE = 32

def encrypt(key, plaintext):
    padded_key = key.ljust(KEY_SIZE, '\0')
    padded_text = plaintext + (BLOCK_SIZE - len(plaintext) % BLOCK_SIZE) * '\0'

    # could also be one of
    #if len(plaintext) % BLOCK_SIZE != 0:
    #    padded_text = plaintext.ljust((len(plaintext) / BLOCK_SIZE) + 1 * BLOCKSIZE), '\0')
    # -OR-
    #padded_text = plaintext.ljust((len(plaintext) + (BLOCK_SIZE - len(plaintext) % BLOCK_SIZE)), '\0')

    r = rijndael.rijndael(padded_key, BLOCK_SIZE)

    ciphertext = ''
    for start in range(0, len(padded_text), BLOCK_SIZE):
        ciphertext += r.encrypt(padded_text[start:start+BLOCK_SIZE])

    encoded = ciphertext.encode('hex_codec')

    return encoded


def decrypt(key, encoded):
    padded_key = key.ljust(KEY_SIZE, '\0')

    ciphertext = encoded.decode('hex_codec')

    r = rijndael.rijndael(padded_key, BLOCK_SIZE)

    padded_text = ''
    for start in range(0, len(ciphertext), BLOCK_SIZE):
        padded_text += r.decrypt(ciphertext[start:start+BLOCK_SIZE])

    plaintext = padded_text.split('\x00', 1)[0]

    return plaintext

def encrypt_cbc(key, iv, plaintext):
    padded_key = key.ljust(KEY_SIZE, '\0')
    padded_iv = iv.ljust(IV_SIZE, '\0')
    padded_text = plaintext + (BLOCK_SIZE - len(plaintext) % BLOCK_SIZE) * '\0'

    # could also be one of
    #if len(plaintext) % BLOCK_SIZE != 0:
    #    padded_text = plaintext.ljust((len(plaintext) / BLOCK_SIZE) + 1 * BLOCKSIZE), '\0')
    # -OR-
    #padded_text = plaintext.ljust((len(plaintext) + (BLOCK_SIZE - len(plaintext) % BLOCK_SIZE)), '\0')

    r = python_Rijndael.new(padded_key,python_Rijndael.MODE_CBC,padded_iv,blocksize=BLOCK_SIZE)

    ciphertext = ''
    for start in range(0, len(padded_text), BLOCK_SIZE):
        ciphertext += r.encrypt(padded_text[start:start+BLOCK_SIZE])

    encoded = ciphertext.encode('hex_codec')

    return encoded

def decrypt_cbc(key, iv, encoded):
    padded_key = key.ljust(KEY_SIZE, '\0')
    padded_iv = iv.ljust(IV_SIZE, '\0')

    ciphertext = encoded.decode('hex_codec')

    r = python_Rijndael.new(padded_key,python_Rijndael.MODE_CBC,padded_iv,blocksize=BLOCK_SIZE)

    padded_text = ''
    for start in range(0, len(ciphertext), BLOCK_SIZE):
        padded_text += r.decrypt(ciphertext[start:start+BLOCK_SIZE])

    plaintext = padded_text.split('\x00', 1)[0]

    return plaintext
