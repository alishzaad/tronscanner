import os
import hashlib
import ecdsa
import requests
import sys
import time
import base58
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore, Style, init
import threading

# Initialize colorama
init()

# --- TRONGRID API SETTINGS ---
TRONGRID_API_KEY = "YOUR_API_KEY"  # اختیاری (اگر نیاز بود اضافه کنید)
TRONGRID_API_URL = "https://api.trongrid.io"

# --- Counter ---
counter = 0
counter_lock = threading.Lock()

# --- Generate Private Key ---
def generate_private_key():
    private_key = os.urandom(32)
    return private_key.hex() if len(private_key) == 32 else None

# --- Generate Tron Address ---
def generate_tron_address(private_hex):
    if private_hex is None:
        print(f"{Fore.RED}Error generating private key{Style.RESET_ALL}")
        return None

    sk = ecdsa.SigningKey.from_string(bytes.fromhex(private_hex), curve=ecdsa.SECP256k1)
    vk = sk.verifying_key
    pub_key = b'\x04' + vk.to_string()
    
    sha256_hash = hashlib.sha256(pub_key).digest()
    ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
    
    address = '41' + ripemd160_hash.hex()
    return tron_base58(address)

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
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            # "TRON-PRO-API-KEY": TRONGRID_API_KEY  # اگر API Key نیاز بود
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()

        # بررسی اینکه آیا کلید "data" در پاسخ وجود دارد و دارای مقدار معتبر است
        if "data" not in data or not data["data"]:
            print(f"{Fore.YELLOW}No data found for address: {address}{Style.RESET_ALL}")
            return 0  # یعنی موجودی 0 TRX

        # استخراج موجودی (موجودی بر حسب SUN است)
        balance_sun = data["data"][0].get("balance", 0)
        balance_trx = balance_sun / 1_000_000  # تبدیل SUN به TRX
        
        return balance_trx
        
    except requests.exceptions.RequestException as e:
        return f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}"
    except Exception as e:
        return f"{Fore.RED}Unexpected Error: {str(e)}{Style.RESET_ALL}"

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
        with ThreadPoolExecutor(max_workers=4) as executor:
            while True:
                # 4 درخواست در ثانیه (مطابق محدودیت TronGrid)
                for _ in range(4):
                    executor.submit(process_address)
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\nOperation stopped by user")

# --- Display Banner ---
if __name__ == "__main__":
    print(f"""
    {Fore.RED}████████╗██████╗░░█████╗░███╗░░██╗
    ╚══██╔══╝██╔══██╗██╔══██╗████╗░██║
    ░░░██║░░░██████╦╝██║░░██║██╔██╗██║
    ░░░██║░░░██╔══██╗██║░░██║██║╚████║
    ░░░██║░░░██████╦╝╚█████╔╝██║░╚███║
    ░░░╚═╝░░░╚═════╝░░╚════╝░╚═╝░░╚══╝{Style.RESET_ALL}
    
    {Fore.GREEN}TRON Address Scanner [TronGrid]{Style.RESET_ALL}
    {Fore.BLUE}• Speed: 4 addresses/second{Style.RESET_ALL}
    """)
    main()
