import deny_rust


def main():
    config = deny_rust.DenyListConfig(words=["malware", "danger", "secret"])
    deny_list = deny_rust.DenyListPlugin(config=config)

    print("test deny_list :",deny_list.scan({"path": "ok danger"}))
    print("test deny_list :", deny_list.scan({"asdf": "        ok"}))

    result1 = deny_list.prompt_pre_fetch({"text": "ok danger"})
    print(f"test prompt_pre_fetch: {result1.violation}")
    result2 = deny_list.prompt_pre_fetch({"asdf": "        ok"})
    print(f"test prompt_pre_fetch: {result2.violation}")


if __name__ == "__main__":
    main()
