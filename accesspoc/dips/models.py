from django.db import models

class Collection(models.Model):
	identifier = models.CharField(max_length=50, primary_key=True)
	title = models.CharField(max_length=200, blank=True)
	creator = models.CharField(max_length=200, blank=True)
	subject = models.CharField(max_length=200, blank=True)
	description = models.TextField(blank=True, null=True)
	publisher = models.CharField(max_length=200, blank=True)
	contributor = models.CharField(max_length=200, blank=True)
	date = models.CharField(max_length=21, blank=True)
	dctype = models.CharField(max_length=200, blank=True)
	dcformat = models.TextField(blank=True, null=True)
	source = models.CharField(max_length=200, blank=True)
	language = models.CharField(max_length=20, blank=True)
	coverage = models.CharField(max_length=200, blank=True)
	rights = models.CharField(max_length=200, blank=True)
	link = models.URLField(blank=True)

	def __str__(self):
		return self.identifier

class DIP(models.Model):
	identifier = models.CharField(max_length=50, primary_key=True)
	ispartof = models.ForeignKey(Collection, related_name='dips')
	title = models.CharField(max_length=200, blank=True)
	creator = models.CharField(max_length=200, blank=True)
	subject = models.CharField(max_length=200, blank=True)
	description = models.TextField(blank=True, null=True)
	publisher = models.CharField(max_length=200, blank=True)
	contributor = models.CharField(max_length=200, blank=True)
	date = models.CharField(max_length=21, blank=True)
	dctype = models.CharField(max_length=200, blank=True)
	dcformat = models.TextField(blank=True, null=True)
	source = models.CharField(max_length=200, blank=True)
	language = models.CharField(max_length=20, blank=True)
	coverage = models.CharField(max_length=200, blank=True)
	rights = models.CharField(max_length=200, blank=True)
	objectszip = models.FileField(blank=True, default=None)
	uploaded = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.identifier

class DigitalFile(models.Model):
	uuid = models.CharField(max_length=32, primary_key=True)
	filepath = models.TextField()
	fileformat = models.CharField(max_length=200)
	formatversion = models.CharField(max_length=200, blank=True, null=True)
	size_bytes = models.IntegerField()
	size_human = models.CharField(max_length=10, blank=True)
	datemodified = models.CharField(max_length=30, blank=True)
	puid = models.CharField(max_length=11, blank=True)
	amdsec = models.CharField(max_length=12)
	hashtype = models.CharField(max_length=7)
	hashvalue = models.CharField(max_length=128)
	dip = models.ForeignKey(DIP, related_name='digital_files')

	def __str__(self):
		return self.uuid

class PREMISEvent(models.Model):
	uuid = models.CharField(max_length=32, primary_key=True)
	eventtype = models.CharField(max_length=200, blank=True)
	datetime = models.CharField(max_length=50, blank=True)
	detail = models.TextField(blank=True, null=True)
	outcome = models.TextField(blank=True, null=True)
	detailnote = models.TextField(blank=True, null=True)
	digitalfile = models.ForeignKey(DigitalFile, related_name='premis_events')

	def __str__(self):
		return self.uuid

