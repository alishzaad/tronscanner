import os
import hashlib
import ecdsa
import requests
import sys
import base58
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import Fore, Style, init
import threading

# Initialize colorama
init()

# --- TRONGRID API SETTINGS ---
TRONGRID_API_URL = "https://api.trongrid.io"

# --- Counter ---
counter = 0
counter_lock = threading.Lock()

# --- Generate Private Key ---
def generate_private_key():
    return os.urandom(32).hex()

# --- Generate Tron Address ---
def generate_tron_address(private_hex):
    try:
        sk = ecdsa.SigningKey.from_string(bytes.fromhex(private_hex), curve=ecdsa.SECP256k1)
        vk = sk.verifying_key
        pub_key = b'\x04' + vk.to_string()
        
        sha256_hash = hashlib.sha256(pub_key).digest()
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
        
        address = '41' + ripemd160_hash.hex()
        return tron_base58(address)
    except Exception as e:
        print(f"{Fore.RED}Error generating Tron address: {e}{Style.RESET_ALL}")
        return None

# --- Base58 Conversion ---
def tron_base58(address_hex):
    try:
        address_bytes = bytes.fromhex(address_hex)
        check_sum = hashlib.sha256(hashlib.sha256(address_bytes).digest()).digest()[:4]
        full_address = address_bytes + check_sum
        return base58.b58encode(full_address).decode()
    except Exception as e:
        print(f"{Fore.RED}Error converting to Base58: {e}{Style.RESET_ALL}")
        return None

# --- Validate Tron Address ---
def is_valid_tron_address(address):
    return address and address.startswith("T") and len(address) == 34

# --- Check Balance via TronGrid ---
def check_tron_balance(address):
    try:
        if not is_valid_tron_address(address):
            print(f"{Fore.RED}Invalid address generated: {address}{Style.RESET_ALL}")
            return "Invalid Address"

        url = f"{TRONGRID_API_URL}/v1/accounts/{address}"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()

        if "data" not in data or not data["data"]:
            return 0  # موجودی 0 TRX

        balance_sun = data["data"][0].get("balance", 0)
        return balance_sun / 1_000_000  # تبدیل به TRX
        
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Request Error: {str(e)}{Style.RESET_ALL}")
        return "Error"
    except Exception as e:
        print(f"{Fore.RED}Unexpected Error: {str(e)}{Style.RESET_ALL}")
        return "Error"

# --- Process Address ---
def process_address():
    global counter
    private_hex = generate_private_key()
    address = generate_tron_address(private_hex)

    if not is_valid_tron_address(address):
        print(f"{Fore.RED}Skipping invalid address: {address}{Style.RESET_ALL}")
        return

    balance = check_tron_balance(address)

    with counter_lock:
        counter += 1
        current_count = counter

    status = (
        f"{Fore.CYAN}#{current_count}{Style.RESET_ALL} | "
        f"{Fore.YELLOW}Private:{Style.RESET_ALL} {private_hex} | "
        f"{Fore.GREEN}Address:{Style.RESET_ALL} {address} | "
        f"{Fore.MAGENTA}Balance:{Style.RESET_ALL} {balance} TRX"
    )
    print(status)

    if isinstance(balance, (int, float)) and balance > 0:
        print(f"\n{Fore.GREEN}!!! FUNDS FOUND !!!{Style.RESET_ALL}")
        with open('found.txt', 'a') as f:
            f.write(f"Private: {private_hex}\nAddress: {address}\nBalance: {balance} TRX\n\n")
        sys.exit(0)

# --- Main Execution ---
def main():
    try:
        with ThreadPoolExecutor(max_workers=10) as executor:  # ۱۰ درخواست همزمان
            while True:
                futures = [executor.submit(process_address) for _ in range(10)]
                for future in as_completed(futures):
                    try:
                        future.result()  # بررسی نتیجه
                    except Exception as e:
                        print(f"{Fore.RED}Thread Error: {e}{Style.RESET_ALL}")
    
    except KeyboardInterrupt:
        print("\nOperation stopped by user")

# --- Display Banner ---
if __name__ == "__main__":
    print(f"""
    {Fore.RED}████████╗██████╗░░█████╗░███╗░░██╗
    ╚══██╔══╝██╔══██╗██╔══██╗████╗░██║
    ░░░██║░░░██████╦╝██║░░██║██╔██╗██║
    ░░░██║░░░██╔══██╗██║░░██║██║╚████║
    ░░░██║░░░██████╦╝╚█████╔╝██║░░███║
    ░░░╚═╝░░░╚═════╝░░╚════╝░╚═╝░░╚══╝{Style.RESET_ALL}
    
    {Fore.GREEN}TRON Address Scanner [TronGrid]{Style.RESET_ALL}
    {Fore.BLUE}• Speed: 10 addresses/second{Style.RESET_ALL}
    """)
    main()
