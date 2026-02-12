import deny_rust


def main():
    config = deny_rust.DenyListConfig(words=["malware", "danger", "secret"])
    deny_list = deny_rust.DenyListPlugin(config=config)
    print("test deny_list :",deny_list.scan({"path": "ok danger"}))
    print("test deny_list :", deny_list.scan({"asdf": "        ok"}))
    result1 = deny_list.prompt_pre_fetch({"text": "ok danger"})
    if result1.violation:
        print("test prompt_pre_fetch (with violation):", {
            "reason": result1.violation.reason,
            "description": result1.violation.description,
            "code": result1.violation.code,
            "plugin_name": result1.violation.plugin_name
        })
    else:
        print("test prompt_pre_fetch (with violation): None")
    
    result2 = deny_list.prompt_pre_fetch({"text": "clean text"})
    if result2.violation:
        print("test prompt_pre_fetch (clean):", {
            "reason": result2.violation.reason,
            "description": result2.violation.description,
            "code": result2.violation.code,
            "plugin_name": result2.violation.plugin_name
        })
    else:
        print("test prompt_pre_fetch (clean): None")


if __name__ == "__main__":
    main()
