#https://www.geeksforgeeks.org/how-to-convert-bytes-to-int-in-python/
integer_value = -12
num_bytes = 4  # Number of bytes for the representation
# Convert integer to bytes (big-endian)
byte_representation = integer_value.to_bytes(num_bytes, byteorder='big', signed=True)
print(byte_representation)
decode = int.from_bytes(byte_representation, byteorder='big', signed=True)
print(decode)

#bytes_of_values = bytes([255,255,255,232])
bytes_of_values = bytes([246,112])
print (bytes_of_values)
print (int.from_bytes(bytes_of_values, byteorder='big', signed=True))
