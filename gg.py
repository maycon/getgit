#!/usr/bin/env python

import urllib
import sys, os
import re
import subprocess

GIT="/usr/local/bin/git"

commom_files = [
	# Repository specific configuration file.
	"config",
	"description",
	"index",

	# Hooks are customization scripts used by various Git commands.
	"hooks/pre-commit.sample",
	"hooks/pre-applypatch.sample",
	"hooks/post-update.sample",
	"hooks/update.sample",
	"hooks/prepare-commit-msg.sample",
	"hooks/pre-push.sample",
	"hooks/applypatch-msg.sample",
	"hooks/pre-rebase.sample",
	"hooks/commit-msg.sample",

	# References are stored in subdirectories of this directory
	"refs/heads/master",
	"refs/remotes/origin/master",

	#"packed-refs",

	# Records of changes made to refs are stored in this directory.
	"logs/HEAD",
	"logs/refs/heads/master",
	"logs/refs/remotes/origin/master",

	"COMMIT_EDITMSG",
	"info/exclude",
	"HEAD",

	# Additional information about the object store
	"objects/info/packs",
	"objects/info/alternates",
	"objects/info/http-alternates"
];

blacklist = []

def mkdir_recursive(path):
	sub_path = "/" if path[0] == "/" else ""
	for folder in path.split('/'):
		sub_path = "%s%s/" % (sub_path, folder)
		if not os.path.exists(sub_path):
			os.mkdir(sub_path)

def extract_hashes(buffer):
	match_obj = re.findall(r'([0-9a-f]{40})', buffer)
	if match_obj:
		return match_obj
	return []

def get_file_lines(filename):
	fd = open(filename)
	lines = fd.readlines()
	fd.close

	return lines

def parse_file_hashes(filename):
	lines = get_file_lines(filename)

	result = []
	for line in lines:
		result += extract_hashes(line)

	return result

def save_file(remote):
	local  = '/'.join(remote.split('/')[2:])
	path   = '/'.join(local.split('/')[:-1])

	if os.path.isfile(local) or remote in blacklist:
		return

	mkdir_recursive(path)
	
	try: # ignore 404
		urlobj.retrieve(remote, local)
		#print "-> %s" % (remote)
		return True
	except:
		return False

def get_object(remote_path, object_hash):

	if object_hash in blacklist:
		return
	
	# Loose
	folder = objhash[:2]
	filename = objhash[2:]
	remote = "%s/objects/%s/%s" % (remote_path, folder, filename)
	if save_file (remote) :
		return True

	# Blacklist the hash
	blacklist.append(object_hash)

def get_pack(remote_path, object_pack_hash):
	if object_pack_hash in blacklist:
		return

	remote = "%s/objects/pack/pack-%s.pack" % (remote_path, object_pack_hash)
	if save_file (remote) :
		return True


if __name__ == "__main__":
	if len(sys.argv) <> 2:
		print "Use %s <http://site/path/to/.git>" % (sys.argv[0])
		sys.exit(-1)


	git_path_remote = sys.argv[1] if sys.argv[1][-1] <> '/' else sys.argv[1][:-1]
	git_path_local = '/'.join(git_path_remote.split('/')[2:])

	print "Remote: %s / Local: %s" % (git_path_remote, git_path_local)

	host = git_path_remote.split('/')[2]

	urlobj = urllib.URLopener()


	print "Host: %s" % (host)
	print "\n[+] Retrieving commom files..."
	for commom_file in commom_files:
		remote = "%s/%s" % (git_path_remote, commom_file)
		save_file(remote)
	

	obj_content_list = []
	for object_file in ['logs/HEAD', 'logs/refs/heads/master', 'logs/refs/remotes/origin/master']:
		log_head_file = "%s/%s" % (git_path_local, object_file)
		print "[+] Retrieving objects files (File: %s)..." % (log_head_file)

		if not os.path.exists(log_head_file):
			print "[-] Cannot retrieve objects file %s. There's not HEAD file." % object_file
			continue

		obj_content_list += parse_file_hashes(log_head_file)


	# unique
	obj_content_list = set(obj_content_list)
	qt_objs = len(obj_content_list)

	# Save each object file
	count = 1
	print "\n[+] Saving existing objects files..."
	for objhash in obj_content_list:
		print "[%d/%d] %s" % (count, qt_objs, objhash)
		count = count+1
		get_object(git_path_remote, objhash)
		

	try:
		git_fsck_result = subprocess.check_output(
			[GIT, '--git-dir=%s' % (git_path_local), 'fsck', '--full'],
			shell=False,
			stderr=subprocess.STDOUT
		)
	except Exception, e:
		git_fsck_result = str(e.output)


	obj_content_list = extract_hashes(git_fsck_result)
	qt_objs = len(obj_content_list)

	count = 1
	print "[+] Saving %d objects" % (qt_objs)
	for objhash in obj_content_list:
		print "[%d/%d] %s" % (count, qt_objs, objhash)
		count = count+1

		get_object(git_path_remote, objhash)


	pack_hashes = parse_file_hashes("%s/objects/info/packs" % (git_path_local))
	qt_packs = len(pack_hashes)

	count = 1
	print "\n[+] Saving %s pack files ..." % (qt_packs)
	for pack_hash in pack_hashes:
		print "[%d/%d] %s" % (count, qt_packs, pack_hash)
		count = count+1

		get_pack(git_path_remote, pack_hash)


	pack_files = [ f for f in os.listdir("%s/objects/pack/" % (git_path_local)) ]
	qt_packs = len(pack_files)

	count = 1
	print "\n[+] Unpacking %s pack files ..." % (qt_packs)
	for pack_file in pack_files:
		print "[%d/%d] %s" % (count, qt_packs, pack_hash)
		count = count+1

		try:
			print subprocess.check_output(
				[GIT, '--git-dir=%s' % (git_path_local), 'unpack-objects', '-q'],
				shell=False,
				stderr=subprocess.STDOUT,
				stdin=open("%s/objects/pack/%s" % (git_path_local, pack_file))
			)
		except Exception, e:
			print str(e)

	print "\nFinished!\n"