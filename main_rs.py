import deny_rust
import time

import plugins.deny_filter.DenyListPlugin


def main():
    words=["malware", "danger", "secret"]
    deny_list = deny_rust.DenyList(words)
    
    start = time.perf_counter()
    result3 = deny_list.scan_str("ok danger")
    elapsed3 = time.perf_counter() - start
    print(f"test scan str: {result3} (took {elapsed3:.6f}s)")

    start = time.perf_counter()
    result4 = deny_list.scan_str("        ok")
    elapsed4 = time.perf_counter() - start
    print(f"test scan str: {result4} (took {elapsed4:.6f}s)")


    start = time.perf_counter()
    result1 = deny_list.scan({"path": "ok danger"})
    elapsed1 = time.perf_counter() - start
    print(f"test deny_list : {result1} (took {elapsed1:.6f}s)")

    start = time.perf_counter()
    result2 = deny_list.scan({"asdf": "        ok"})
    elapsed2 = time.perf_counter() - start
    print(f"test deny_list : {result2} (took {elapsed2:.6f}s)")




if __name__ == "__main__":
    main()