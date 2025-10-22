import os

import pymysql
import sqlparse
from dotenv import dotenv_values

_dotenv = dotenv_values('.flaskenv')


def _config(key: str, default: str) -> str:
    """Read configuration value from environment first, then .flaskenv, fallback to default."""
    return os.getenv(key) or _dotenv.get(key) or default


# MySql配置信息
HOST = _config('MYSQL_HOST', '127.0.0.1')
PORT = int(_config('MYSQL_PORT', 3306))
DATABASE = _config('MYSQL_DATABASE', 'AdminFlask')
USERNAME = _config('MYSQL_USERNAME', 'root')
PASSWORD = _config('MYSQL_PASSWORD', '123456')


def is_exist_database():
    db = pymysql.connect(
        host=HOST,
        port=PORT,
        user=USERNAME,
        password=PASSWORD,
        charset='utf8mb4')
    cursor = db.cursor()
    sql = "SELECT COUNT(DISTINCT `TABLE_NAME`) AS anyAliasName FROM `INFORMATION_SCHEMA`.`COLUMNS` WHERE `table_schema` = '%s';" % DATABASE
    res = cursor.execute(sql)
    results = cursor.fetchall()
    db.close()
    return results


def init_database():
    db = pymysql.connect(
        host=HOST,
        port=PORT,
        user=USERNAME,
        password=PASSWORD,
        charset='utf8mb4')
    cursor = db.cursor()
    sql = "CREATE DATABASE IF NOT EXISTS %s CHARSET=utf8 COLLATE=utf8_general_ci;" % DATABASE
    res = cursor.execute(sql)
    db.close()
    return res


def execute_fromfile(filename):
    db = pymysql.connect(
        host=HOST,
        port=PORT,
        user=USERNAME,
        password=PASSWORD,
        database=DATABASE,
        charset='utf8')
    fd = open(filename, 'r', encoding='utf-8')
    cursor = db.cursor()
    sqlfile = fd.read()
    sqlfile = sqlparse.format(sqlfile, strip_comments=True).strip()

    sqlcommamds = sqlfile.split(';')

    for command in sqlcommamds:
        try:
            cursor.execute(command)
            db.commit()

        except Exception as msg:

            db.rollback()
    db.close()


def init_db():
    if is_exist_database()[0][0] > 0:
        print('数据库%s不为空，不进行初始化操作' % str(DATABASE))
        return
    if init_database():
        print('数据库%s创建成功' % str(DATABASE))
    execute_fromfile('init_db.sql')
    print('表创建成功')
