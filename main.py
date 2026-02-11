import deny_rust


def main():
    config = deny_rust.DenyListConfig(words=["malware", "danger", "secret"])
    print("Hello from deny-rust!")


if __name__ == "__main__":
    main()
