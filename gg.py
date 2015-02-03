#!/usr/bin/env python2

import urllib
import sys, os
import re
import subprocess

commom_files = [
	"hooks/pre-commit.sample",
	"hooks/pre-applypatch.sample",
	"hooks/post-update.sample",
	"hooks/update.sample",
	"hooks/prepare-commit-msg.sample",
	"hooks/pre-push.sample",
	"hooks/applypatch-msg.sample",
	"hooks/pre-rebase.sample",
	"hooks/commit-msg.sample",
	"refs/remotes/origin/master",
	"refs/heads/master",
	"index",
	"config",
	"description",
	"logs/refs/remotes/origin/master",
	"logs/refs/heads/master",
	"logs/HEAD",
	"COMMIT_EDITMSG",
	"info/exclude",
	"HEAD"
];


def mkdir_recursive(path):
	sub_path = "/" if path[0] == "/" else ""
	for folder in path.split('/'):
		sub_path = "%s%s/" % (sub_path, folder)
		if not os.path.exists(sub_path):
			os.mkdir(sub_path)

def extract_object_hashes(buffer):
	match_obj = re.findall(r'([0-9a-f]{40})', buffer)
	if match_obj:
		return match_obj
	return []

def parse_head_file_objects(filename):
	fd = open(filename)
	lines = fd.readlines()
	fd.close

	result = []
	for line in lines:
		result += extract_object_hashes(line)

	return result

def save_file(remote):
	local  = '/'.join(remote.split('/')[2:])
	path   = '/'.join(local.split('/')[:-1])
	
	mkdir_recursive(path)
	
	try: # ignore 404
		urlobj.retrieve(remote, local)
		print "%s" % (remote)
	except:
		pass


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
		log_head_file = "%s/%s" % ('/'.join(git_path_remote.split('/')[2:]), object_file)
		print "\n[+] Retrieving objects files (File: %s)..." % (log_head_file)

		if not os.path.exists(log_head_file):
			print "[-] Cannot retrieve objects file %s. There's not HEAD file." % object_file
			continue

		obj_content_list += parse_head_file_objects(log_head_file)


	# unique
	obj_content_list = set(obj_content_list)

	# Save each object file
	print "\n[+] Existing..."
	for objhash in obj_content_list:
		folder = objhash[:2]
		filename = objhash[2:]
		remote = "%s/objects/%s/%s" % (git_path_remote, folder, filename)
		save_file (remote)
		

	# Missing and corrupted
	print "\n[+] Missing"
	try:
		git_fsck_result = subprocess.check_output(
			['/usr/bin/git', '--git-dir=%s' % (git_path_local), 'fsck', '--full'],
			shell=False,
			stderr=subprocess.STDOUT
		)
	except Exception, e:
		git_fsck_result = str(e.output)


	obj_content_list = extract_object_hashes(git_fsck_result)
	for objhash in obj_content_list:
		folder = objhash[:2]
		filename = objhash[2:]
		remote = "%s/objects/%s/%s" % (git_path_remote, folder, filename)
		save_file (remote)

