__sql_magic = None


def _get_sql_magic():
    if __sql_magic is None:
        raise RuntimeError("SqlMagic has not been loaded yet.")

    return __sql_magic


def _set_sql_magic(sql_magic):
    global __sql_magic
    __sql_magic = sql_magic


def _config_feedback_all():
    return _get_sql_magic().feedback >= 2


def _config_feedback_normal_or_more():
    return _get_sql_magic().feedback >= 1
