import zlib  
  
def compress_file(filename, compression_level=9):  
    # Read file  
    with open(filename, 'rb') as f_in:  
        data = f_in.read()  
      
    # Compress data  
    compressed_data = zlib.compress(data, compression_level)  
      
    # Write compressed data to a new file  
    with open(filename + '.zlib', 'wb') as f_out:  
        f_out.write(compressed_data)  
  
# Usage  
compress_file('ip_ranges.csv')  
