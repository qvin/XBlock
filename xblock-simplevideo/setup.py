from setuptools import setup

setup(
	name='xblock-simplevideo',
	version='0.1',
	description='SimpleVideo XBlock tutorial sample',
	py_modules=['simplevideo'],
	install_requires=['XBlock'],
	entry_points={
		'xblock.v1':[
			'simplevideo=simplevideo:SimpleVideoBlock',
		]
	}
)
