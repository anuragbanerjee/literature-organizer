#!/usr/bin/env python
#
# Checks through Table of Contents and metadata to acertain title and author information.
# 

#general
import os, sys, re

# pdf title via table of contents
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument

# get pdf metadata
from pyPdf import PdfFileReader

#epub info
from zipfile import ZipFile
import lxml.etree as ET
from StringIO import StringIO

namespace = {'p': 'urn:oasis:names:tc:opendocument:xmlns:container', 'dc':'http://purl.org/dc/elements/1.1/'}

#
# general functions
#

failed             = "[BAD INPUT]    "
worked             = "[PROCESSED]"
unsupported        = "[UNSUPPORTED]  "
acceptable_formats = ["pdf", "epub"]
# path             = "/Users/anuragbanerjee/Desktop/testpapers/"
path               = sys.argv[1:] or ["/Users/anuragbanerjee/Dropbox/Books/"]

def clean_title(title):
	title = title.replace("/", ": ").replace(":", " -")
	title = re.sub('<[^>]*>', '', title) if title else title # fixes malformed titles with tags
	return title

def clean_author(raw_author):
	if raw_author.count(", ") == 1 and \
	   ", " in raw_author and \
	   " and" not in raw_author and \
	   " with" not in raw_author:
		author = raw_author.split(",")
		author = author[1].strip() + " " + author[0].strip()
		author = author + " - "
		author = author.replace("/", ": ")
		return author
	elif raw_author:
		return raw_author.replace("/", ": ") + " - "
	else: return ""

#
# EPUBs
#

def xgettext(root, path):
  try:
    return root.xpath(path, namespaces=namespace)[0].text
  except:
    return ""

def getEpubInfo(filename):
	try:
		epub = ZipFile(filename)

		meta = ET.ElementTree()
		meta.parse(StringIO(epub.read("META-INF/container.xml")))

		root = ET.ElementTree()
		rootfilename = meta.xpath("//p:rootfile/@full-path", namespaces=namespace)[0]
		root.parse(StringIO(epub.read(rootfilename)))

		title = xgettext(root, "//dc:title")
		author = xgettext(root, "//dc:creator")
		publisher = xgettext(root, "//dc:publisher")
		identifier = xgettext(root, "//dc:identifier")
		language = xgettext(root, "//dc:language")

		return {'title':title, 'author':author, 'publisher':publisher, 'identifier':identifier, 'language':language}
	except:
		return None

def checkepub(file, counter):
	file_name = file.split("/")[-1]
	file_extension = file_name.split(".")[-1]
	file_name = file_name[:len(file_extension) * -1]
	try:
		info = getEpubInfo(file)
		title = info['title']
		author = clean_author(info['author'])

		title = clean_title(title)

		counter += 1
		print worked, str(counter).zfill(3), author + title
		return author + title, counter
	except:
		print '\033[91m' + failed + "\033[0m", file_name + "." + file_extension
		return file_name, counter

#
# PDFs
#

def get_info(file):
	file_size = os.path.getsize(file)
	isJournal = file_size <= 1050000 # 1.05 mb 

	from_metadata = via_metadata(file)
	from_toc = via_toc(file) if isJournal else None

	try:
		if not from_toc or is_bad(from_toc['/Title']): from_toc = None
		if not from_metadata or is_bad(from_metadata['/Title']) : from_metadata = None
		title = from_metadata or from_toc or "not found"
	except Exception, e:
		title = "not found"
	return title

def via_toc(path):
	try:
		titles = []
		infile = open(path, 'rb')
		parser = PDFParser(infile)
		document = PDFDocument(parser)
		toc = list()
		title = [(level, title) for (level,title,dest,a,structelem) in document.get_outlines()][0][1]
		return {
			"/Title": title,
			"/Author" : ""
		}
	except Exception, e:
		return None

def via_metadata(path):
	try:
		return PdfFileReader(open(path, 'rb')).getDocumentInfo()
		# info = {k[1:].lower():v for k,v in docInfo.items()} # removes crap
		# return info['title']
	except Exception, e:
		return None

def is_bad(title):
	if not title: return True

	crap_titles = ["Introduction", ". Introduction", "1 Introduction", "I Introduction", "not found", "n", "Table of Contents", "1 Table of Contents", "I Table of Contents", "Cover","Abstract", "Chapter "]
	crap_endings= ["dvi", "ps", "eps", "pdf", "doc", "epub", "mobi"]

	bad_title = title in crap_titles
	bad_title_ending = title.split(".")[-1] in crap_endings
	too_short = len(title) <= 10 and len(title.split(" ")) < 2

	isBad = bad_title or bad_title_ending or too_short
	return isBad

def checkpdf(file, counter):
	file_name = file.split("/")[-1]
	file_extension = file_name.split(".")[-1]
	file_name = file_name[:(len(file_extension) * -1) - 1]

	info = get_info(file)
	if not info: return file_name, counter

	title = "" if '/Title' not in info else info['/Title']
	author = "" if '/Author' not in info else info['/Author']
	title = clean_title(title)
	author = clean_author(author)

	if is_bad(title):
		print '\033[91m' + failed + "\033[0m", file_name
		return file_name, counter
	else:
		counter += 1
		print worked, str(counter).zfill(3), author + title
		return author + title, counter
	return file_name, counter

counter = 0
search = []
for path in path:
	if os.path.isdir(path):
		path = path + "/" if path[-1] != "/" else path
		files = os.listdir(path)
		query = [path + file for file in files if file.split(".")[-1] in acceptable_formats and file[0] != "."]
		search = search + query
	else:
		search.append(path)

for file in search:
	if os.path.isdir(file) : continue
	file_name = file.split("/")[-1]
	file_extension = file_name.split(".")[-1]
	path = "/".join(file.split("/")[:-1]) + "/"
	if file_extension == "epub":
		new_name, counter = checkepub(file, counter)
		os.rename(file, path + new_name + "." + file_extension)
	elif file_extension == "pdf":
		new_name, counter = checkpdf(file, counter)
		os.rename(file, path + new_name + "." + file_extension)
	else:
		print '\033[93m' + unsupported + "\033[0m", file_name

percent = 100*counter/len(search)
print "----------------------------------------\n\n", counter, "titles found out of", len(search), ",", str(percent) + "% success" 