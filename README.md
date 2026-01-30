# mrdpm

设置了gitignore，忽略了缓存文件、权重文件和各类AI代码的初始化文件，详情查看[.gitignore](.gitignore)
如有需要，从js的源码中下载获取

如果需要更改.gitignore，请联系仓库主

为避免一些不必要的错误，奉上一些温馨提示：
1. 根目录下的requirements.txt文件目前没有构建完全，请在mrdpm目录下的requirements.txt找到自己没下全的包
2. 直接pip下的torch默认是cpu版本，gpu版本则需要根据电脑的配置安装对应版本