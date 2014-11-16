#!/usr/bin/env python

import argparse
import httplib2
import json
import os
# Google APIs
from apiclient.discovery import build
from oauth2client import client
from oauth2client.file import Storage
from oauth2client.tools import run_flow
from oauth2client.tools import argparser

# Globals
debug = False


def main():
  """
  Parse the command line positional and optional arguments.
  This is the highest level procedure that invokes the real workers.
  """
  global debug

  parser = argparse.ArgumentParser(
    description='ipynb2blogger.py is a tool for posting iPython notebooks to blogger.',
    parents=[argparser],
    epilog='Written by A.Adcroft, 2014 (https://github.com/Adcroft).')
  parser.add_argument('-d', '--debug', action='store_true', help='Turn on debugging.')
  subparsers = parser.add_subparsers()#help='sub-command help')

  parser_listblogs = subparsers.add_parser('listblogs', help='Lists blogs you can post to.')
  parser_listblogs.set_defaults(action=listBlogs)

  cArgs = parser.parse_args()
  if cArgs.debug: debug = cArgs.debug
  if debug: print 'cArgs=',cArgs
  if debug: print '__file__=',__file__
  cArgs.action(cArgs)


def listBlogs(args):
  """
  Lists blogs associated with authenticated user.
  """
  global debug
  if debug: print 'listBlogs:args=',args

  service, http = authenticate()

  users = service.users()
  if debug: print 'users=',users
  
  # Retrieve this user's profile information
  thisuser = users.get(userId='self').execute(http=http)
  if debug: print 'thisuser=',thisuser
  print 'This user\'s display name is: %s' % thisuser['displayName']

  # Retrieve the list of Blogs this user has write privileges on
  blogs = service.blogs()
  if debug: print 'blogs=',blogs
  thisusersblogs = blogs.listByUser(userId='self').execute()
  if debug: print 'thisusersblogs=',thisusersblogs
  if 'items' in thisusersblogs:
    for blog in thisusersblogs['items']:
      if debug: print 'blog=',blog
      print 'The blog named \'%s\' is at: %s' % (blog['name'], blog['url'])
  else: print 'No blogs found'


def authenticate():
  """
  Handles authentication.

  Returns service object, Http object.
  """
  global debug

  # Create storage for credentials
  storage = Storage('credentials.dat')
  if debug: print 'storage=',storage

  # Set up a Flow object to be used for authentication
  client_secrets = os.path.join(os.path.dirname(__file__),'client_secrets.json')
  flow = client.flow_from_clientsecrets(client_secrets,
      scope='https://www.googleapis.com/auth/blogger',
      message='Eeek')
  if debug: print 'flow=',flow

  # Load credentials from Storage object, or run(flow)
  credentials = storage.get() # Returns None if no credentials found
  if debug: print 'credentials=',credentials
  if credentials is None or credentials.invalid:
    credentials = run_flow(flow, storage, flags=cArgs)
    if debug: print '2:credentials=',credentials

  # Create an httplib2.Http object to handle our HTTP requests, and authorize it
  # using the credentials.authorize() function.
  http = httplib2.Http()
  http = credentials.authorize(http)
  if debug: print 'http=',http

  # Create a service object
  service = build('blogger', 'v3', http=http)
  if debug: print 'service=',service

  return service, http


# Invoke the top-level procedure
if __name__ == '__main__': main()
