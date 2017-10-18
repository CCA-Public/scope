from django.db import models

class Department(models.Model):
	name = models.CharField(max_length=100)

	def __str__(self):
		return self.name

class Collection(models.Model):
	identifier = models.CharField(max_length=50, primary_key=True)
	ispartof = models.ForeignKey(Department, related_name='collections')
	title = models.CharField(max_length=200, null=True)
	creator = models.CharField(max_length=200, null=True)
	subject = models.CharField(max_length=200, null=True)
	description = models.TextField(null=True)
	publisher = models.CharField(max_length=200, null=True)
	contributor = models.CharField(max_length=200, null=True)
	date = models.CharField(max_length=21, null=True)
	dctype = models.CharField(max_length=200, null=True)
	dcformat = models.TextField(null=True)
	source = models.CharField(max_length=200, null=True)
	language = models.CharField(max_length=20, null=True)
	coverage = models.CharField(max_length=200, null=True)
	rights = models.CharField(max_length=200, null=True)
	link = models.URLField()

	def __str__(self):
		return self.identifier

class DIP(models.Model):
	identifier = models.CharField(max_length=50, primary_key=True)
	ispartof = models.ForeignKey(Collection, related_name='dips')
	title = models.CharField(max_length=200, null=True)
	creator = models.CharField(max_length=200, null=True)
	subject = models.CharField(max_length=200, null=True)
	description = models.TextField(null=True)
	publisher = models.CharField(max_length=200, null=True)
	contributor = models.CharField(max_length=200, null=True)
	date = models.CharField(max_length=21, null=True)
	dctype = models.CharField(max_length=200, null=True)
	dcformat = models.TextField(null=True)
	source = models.CharField(max_length=200, null=True)
	language = models.CharField(max_length=20, null=True)
	coverage = models.CharField(max_length=200, null=True)
	rights = models.CharField(max_length=200, null=True)
	metsfile = models.FileField(null=True, default=None)
	objectszip = models.FileField(null=True, default=None)
	uploaded = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.objectid

class DigitalFile(models.Model):
	uuid = models.CharField(max_length=32, primary_key=True)
	filepath = models.TextField()
	fileformat = models.CharField(max_length=200)
	formatversion = models.CharField(max_length=200, null=True)
	size_bytes = models.IntegerField()
	size_human = models.CharField(max_length=10, null=True)
	datemodified = models.CharField(max_length=30, null=True)
	puid = models.CharField(max_length=11, null=True)
	amdsec = models.CharField(max_length=12)
	hashtype = models.CharField(max_length=7)
	hashvalue = models.CharField(max_length=128)
	dip = models.ForeignKey(DIP, related_name='digital_files')

	def __str__(self):
		return self.uuid

class PREMISEvent(models.Model):
	uuid = models.CharField(max_length=32, primary_key=True)
	eventtype = models.CharField(max_length=200, null=True)
	datetime = models.CharField(max_length=50, null=True)
	detail = models.TextField(null=True)
	outcome = models.TextField(null=True)
	detailnote = models.TextField(null=True)
	digitalfile = models.ForeignKey(DigitalFile, related_name='premis_events')

	def __str__(self):
		return self.uuid

