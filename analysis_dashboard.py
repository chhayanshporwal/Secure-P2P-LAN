import os
import time
import matplotlib.pyplot as plt
from crypto_utils import generate_ecc_key_pair, generate_aes_key, encrypt_chunk, decrypt_chunk

def calculate_avalanche_effect(aes_key):
    # Plaintext of 16 bytes (128 bits)
    pt1 = b'A' * 16
    
    # Change exactly 1 bit in pt1 to get pt2
    # 'A' is 01000001 in binary. We change the last bit to 0: 01000000 ('@')
    pt2 = b'@' + b'A' * 15
    
    ct1 = encrypt_chunk(pt1, aes_key)
    ct2 = encrypt_chunk(pt2, aes_key)
    
    diff_bits = 0
    total_bits = len(ct1) * 8
    
    for b1, b2 in zip(ct1, ct2):
        xor = b1 ^ b2
        diff_bits += bin(xor).count('1')
        
    return (diff_bits / total_bits) * 100

def run_analysis():
    sizes_mb = [1, 5, 10, 25, 50]
    enc_times = []
    dec_times = []
    
    aes_key = generate_aes_key()
    
    print("\n" + "="*50)
    print(" AUTOMATED PERFORMANCE ANALYSIS DASHBOARD ")
    print("="*50)
    print(f"{'File Size (MB)':<15} | {'Encryption (s)':<15} | {'Decryption (s)':<15}")
    print("-" * 50)
    
    for size in sizes_mb:
        # Create dummy data
        data = os.urandom(size * 1024 * 1024)
        
        # Chunking mechanism mimicking the real app (8192 bytes)
        chunks = [data[i:i+8192] for i in range(0, len(data), 8192)]
        
        # Time Encryption
        start = time.time()
        encrypted_chunks = []
        for chunk in chunks:
            encrypted_chunks.append(encrypt_chunk(chunk, aes_key))
        enc_time = time.time() - start
        enc_times.append(enc_time)
        
        # Time Decryption
        start = time.time()
        for chunk in encrypted_chunks:
            decrypt_chunk(chunk, aes_key)
        dec_time = time.time() - start
        dec_times.append(dec_time)
        
        print(f"{size:<15} | {enc_time:<15.4f} | {dec_time:<15.4f}")
        
    print("-" * 50)
    
    av_effect = calculate_avalanche_effect(aes_key)
    print(f"Avalanche Effect (1-bit change in plaintext): {av_effect:.2f}%")
    print("(Ideal cryptographic Avalanche Effect is ~50% or higher)")
    print("=" * 50)
    
    # Generate Graphs
    plt.figure(figsize=(10, 5))
    
    plt.plot(sizes_mb, enc_times, label='Encryption Time (s)', marker='o', color='blue', linewidth=2)
    plt.plot(sizes_mb, dec_times, label='Decryption Time (s)', marker='o', color='orange', linewidth=2)
    
    plt.title('Hybrid AES-ECC Performance Analysis (Time vs File Size)')
    plt.xlabel('File Size (MB)')
    plt.ylabel('Time (Seconds)')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    
    graph_path = "performance_graph.png"
    plt.savefig(graph_path)
    print(f"\n[SUCCESS] Graph successfully saved as '{graph_path}'")
    print("[INFO] You can use these metrics and the graph directly in your Research Paper!\n")

if __name__ == "__main__":
    run_analysis()
