from setuptools import setup

setup(name='littlefield',
      version='0.3.3',
      description='API for the Littlefield simulation',
      url='http://github.com/yi-jiayu/littlefield',
      author='Jiayu Yi',
      author_email='yijiayu@gmail.com',
      license='MIT',
      packages=['littlefield'],
      install_requires=[
          'requests',
      ],
      zip_safe=False)
