from werkzeug.exceptions import BadRequest


def xss_escape(s: str):
    if s is None:
        return None
    return (
        s.replace("&", "&amp;")
        .replace(">", "&gt;")
        .replace("<", "&lt;")
        .replace("'", "&#39;")
        .replace('"', "&#34;")
    )


def check_data(schema, data):
    errors = schema.validate(data)
    if not errors:
        return
    msg = "参数校验失败"
    for key, values in errors.items():
        if values:
            msg = f"{key}{values[0]}"
            break
    raise BadRequest(msg)
