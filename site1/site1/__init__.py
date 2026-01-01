import pymysql

# Đánh lừa phiên bản mysqlclient
pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.install_as_MySQLdb()

# Đánh lừa phiên bản MariaDB để vượt qua lỗi 10.4.17
from django.db.backends.mysql.base import DatabaseWrapper
DatabaseWrapper.display_name = 'MariaDB'
DatabaseWrapper.data_types['DateTimeField'] = 'datetime'