#!/usr/bin/env python

import urllib
import sys, os
import re
import subprocess

import threading
import time

THREADS=10

commom_files = [
	# Repository specific configuration file.
	"config",
	"description",
	"index",

	# Hooks are customization scripts used by various Git commands.
	#"hooks/pre-commit.sample",
	#"hooks/pre-applypatch.sample",
	#"hooks/post-update.sample",
	#"hooks/update.sample",
	#"hooks/prepare-commit-msg.sample",
	#"hooks/pre-push.sample",
	#"hooks/applypatch-msg.sample",
	#"hooks/pre-rebase.sample",
	#"hooks/commit-msg.sample",

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

################################# Handle CTRL+C ##########################
import signal

def signal_handler(signal, frame):
        print('You pressed Ctrl+C!')
        sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
##########################################################################

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
	try:
		fd = open(filename)
		lines = fd.readlines()
		fd.close

		return lines
	except:
		pass

	return []

def parse_file_hashes_old(filename):
	lines = get_file_lines(filename)

	result = []
	for line in lines:
		result += extract_hashes(line)

	return result


def parse_file_hashes(filename):
	lines = get_file_lines(filename)
	return [hash_value for line in lines for hash_value in extract_hashes(line)]


def wait_threads():
	while threading.active_count() > 1:
		time.sleep(0.5)


def save_file_thread(remote):
	local  = '/'.join(remote.split('/')[2:])
	path   = '/'.join(local.split('/')[:-1])
	
	if os.path.isfile(local):
		return
	try:
		mkdir_recursive(path)
	except:
		pass
	
	try: # ignore 404
		urlobj.retrieve(remote, local)
	except:
		return False

	return True

def save_file(remote):
	while threading.active_count() >= THREADS:
		time.sleep(0.5)
	
	th = threading.Thread(target=save_file_thread, args=(remote,))
	th.daemon = True
	th.start()

def get_object(remote_path, object_hash):

	# Loose
	folder = objhash[:2]
	filename = objhash[2:]
	remote = "%s/objects/%s/%s" % (remote_path, folder, filename)
	return True if save_file (remote) else False
		

def get_pack(remote_path, object_pack_hash):
	remote = "%s/objects/pack/pack-%s.pack" % (remote_path, object_pack_hash)
	return True if save_file (remote) else False


if __name__ == "__main__":
	if len(sys.argv) <> 2:
		print "Use %s <http://site/path/to/.git>" % (sys.argv[0])
		sys.exit(-1)

	urlobj = urllib.URLopener()

	git_path_remote = sys.argv[1] if sys.argv[1][-1] <> '/' else sys.argv[1][:-1]
	git_path_local = '/'.join(git_path_remote.split('/')[2:])
	host = git_path_remote.split('/')[2]

	print "[i] Remote: %s" % (git_path_remote)
	print "[i] Local: %s" % (git_path_local)
	print "[i] Host: %s" % (host)
	print "\n"

	qt_commom_files = len(commom_files)
	count = 1
	print "\n[+] Retrieving %s commom files..." % (qt_commom_files)

	for commom_file in commom_files:
		print "[%d/%d] %s" % (count, qt_commom_files, commom_file)
		count = count + 1

		remote = "%s/%s" % (git_path_remote, commom_file)
		save_file(remote)
	
	wait_threads()

	obj_content_list = []
	for object_file in ['logs/HEAD', 'logs/refs/heads/master', 'logs/refs/remotes/origin/master']:
		log_head_file = "%s/%s" % (git_path_local, object_file)

		if not os.path.exists(log_head_file):
			print "[-] Cannot retrieve objects file %s. There's not HEAD file." % object_file
			continue

		obj_content_list += parse_file_hashes(log_head_file)

	wait_threads()

	# unique
	obj_content_list = set(obj_content_list)
	qt_objs = len(obj_content_list)

	# Save each object file
	count = 1
	print "\n[+] Saving %d existing objects files..." % (qt_objs)
	for objhash in obj_content_list:
		print "[%d/%d] %s" % (count, qt_objs, objhash)
		count = count+1
		get_object(git_path_remote, objhash)
		
	wait_threads()

	pack_hashes = parse_file_hashes("%s/objects/info/packs" % (git_path_local))
	qt_packs = len(pack_hashes)

	count = 1
	print "\n[+] Saving %s pack files ..." % (qt_packs)
	for pack_hash in pack_hashes:
		print "[%d/%d] %s" % (count, qt_packs, pack_hash)
		count = count+1

		get_pack(git_path_remote, pack_hash)


	wait_threads()

	pack_files = []
	try:
		pack_files = [ f for f in os.listdir("%s/objects/pack/" % (git_path_local)) ]
		qt_packs = len(pack_files)
	except:
		pass

	count = 1
	print "\n[+] Unpacking %s pack files ..." % (qt_packs)
	for pack_file in pack_files:
		print "[%d/%d] %s" % (count, qt_packs, pack_hash)
		count = count+1

		try:
			print subprocess.check_output(
				['git', '--git-dir=%s' % (git_path_local), 'unpack-objects', '-q'],
				shell=False,
				stderr=subprocess.STDOUT,
				stdin=open("%s/objects/pack/%s" % (git_path_local, pack_file))
			)
		except Exception, e:
			pass

	wait_threads()

	blacklist = []
	tries = 0
	while True:
		try:
			git_fsck_result = subprocess.check_output(
				['git', '--git-dir=%s' % (git_path_local), 'fsck', '--full'],
				shell=False,
				stderr=subprocess.STDOUT
			)
		except Exception, e:
			git_fsck_result = str(e.output) if hasattr(e, 'output') else ''

		obj_content_list = extract_hashes(git_fsck_result)
		new_obj_hashes = [h for h in obj_content_list if not h in blacklist]
		qt_objs = len(obj_content_list)
		qt_new = len(new_obj_hashes)

		print "\n[+] git-fsck returns %d objects files (%s new)." % (qt_objs, qt_new)

		if qt_new = 0:
			break

		count = 1
		print "\n[+] Saving %d recoveried objects files..." % (qt_new)
		for objhash in new_obj_hashes:
			print "[%d/%d] %s" % (count, qt_objs, objhash)
			count = count+1

			if not get_object(git_path_remote, objhash):
				blacklist.append(objhash)

		wait_threads()


	print "\n[+] Finishing..\n"

	wait_threads()

	print "[*] Good bye!\n"
	sys.exit(0)
	

