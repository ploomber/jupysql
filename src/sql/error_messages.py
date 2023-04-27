import sqlglot


def detail(msg, query=None):
    msg = str(msg)
    return_msg = "\nLooks like there is a syntax error " "in your query\n"
    if "syntax error" in msg:
        query_list = query.split(";")
        for q in query_list:
            try:
                q = q.strip()
                parse = sqlglot.transpile(q)
                if q.upper() not in [suggestion.upper() for suggestion in parse]:
                    return_msg += f"Did you mean : {parse}\n"

            except sqlglot.errors.ParseError as e:
                err = e.errors
                for item in err:
                    return_msg += (
                        f"Syntax Error in {q}: {item['description']} at "
                        f"Line {item['line']}, Column {item['col']}\n"
                    )

        return return_msg

    if "fe_sendauth: no password supplied" in msg:
        return (
            "\nLooks like you have run into some issues. "
            "Review our DB connection via URL strings guide: "
            "https://jupysql.ploomber.io/en/latest/connecting.html ."
            " Using Ubuntu? Check out this guide: "
            "https://help.ubuntu.com/community/PostgreSQL#fe_sendauth:_"
            "no_password_supplied\n"
        )

    return None
