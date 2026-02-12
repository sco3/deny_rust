import deny_rust


def main():
    words=["malware", "danger", "secret"]
    deny_list = deny_rust.DenyList(words)

    print("test deny_list :",deny_list.scan({"path": "ok danger"}))
    print("test deny_list :", deny_list.scan({"asdf": "        ok"}))


if __name__ == "__main__":
    main()
