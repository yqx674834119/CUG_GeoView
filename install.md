## paddlepaddle 和 paddleRS 安装 
```bash
conda create -n PaddleRS37 python==3.7
# conda remove -n PaddleRS37 --all
# 安装 paddlepaddle
conda install paddlepaddle-gpu==2.4.2 cudatoolkit=11.7 -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/Paddle/ -c conda-forge
# 安装 paddlers
git clone -b release/1.0 https://github.com/PaddlePaddle/PaddleRS.git

cd PaddleRS
pip install "setuptools<=65.5.0"
pip install -r requirements.txt
pip install -e .
conda install gdal
pip install cryptography
```

## 基础配置
MySQL >= 5.7
```bash
# 更新包索引
sudo apt update
# 安装 MySQL 服务端和客户端
sudo apt install mysql-server mysql-client -y
# 查看版本
mysql --version

sudo service mysql start

sudo mysql
CREATE USER 'paddle_rs'@'localhost' IDENTIFIED BY 'Yqx090315.';
GRANT ALL PRIVILEGES ON paddle_rs.* TO 'paddle_rs'@'localhost';
FLUSH PRIVILEGES;
```

Node.js >= 16.0
```bash
# 安装依赖
sudo apt update
sudo apt install -y curl gnupg

# 下载并安装 NodeSource 脚本（Node.js 18）
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -

# 安装 Node.js
sudo apt install -y nodejs

node -v
npm -v

```

## 项目配置
接着，运行如下命令以安装Web后端的所有依赖：
```bash
pip install -r backend/requirements.txt
```

## 启动 Web 后端
在项目根目录执行如下指令以启动 Web 后端：
```bash
conda activate PaddleRS37
cd backend
python app.py
```
启动后，数据库将自动得到初始化。