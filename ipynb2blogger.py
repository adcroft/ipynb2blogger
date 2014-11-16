#!/usr/bin/env python

import argparse
import httplib2
import json
import logging
import os
# Google APIs
from apiclient.discovery import build
from oauth2client import client
from oauth2client.file import Storage
from oauth2client.tools import run_flow
from oauth2client.tools import argparser
from googleapiclient.errors import HttpError


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

  parser_whoami = subparsers.add_parser('whoami', help='Display username you are authenticated as.')
  parser_whoami.set_defaults(action=whoAmI)

  parser_listblogs = subparsers.add_parser('listblogs', help='Lists blogs the authenticated user can post to.')
  parser_listblogs.set_defaults(action=listBlogs)

  parser_listposts = subparsers.add_parser('list', help='Lists published posts in blog at url.')
  parser_listposts.add_argument('url', type=str, help='URL of blogger blog.')
  parser_listposts.set_defaults(action=listPosts)
  group = parser_listposts.add_mutually_exclusive_group()
  group.add_argument('-d', '--draft', action='store_true', help='List draft posts.')
  group.add_argument('-s', '--scheduled', action='store_true', help='List scheduled posts.')

  cArgs = parser.parse_args()
  #if cArgs.debug:
  #  httplib2.debuglevel = 4

  cArgs.action(cArgs, debug=cArgs.debug)


def whoAmI(args, debug=False):
  """
  Displays name of authenticated user.
  """

  service, http = authenticate(args)

  users = service.users()
  if debug: print 'users =',users
  
  # Retrieve this user's profile information
  request = users.get(userId='self')
  if debug: print 'users().get(userId="self") =',request.to_json()
  response = request.execute(http=http)
  if debug: print 'response =',json.dumps(response,indent=2)
  print 'This user\'s display name is: %s' % response['displayName']


def listBlogs(args, debug=False):
  """
  Lists blogs associated with authenticated user.
  """

  service, http = authenticate(args)

  # Retrieve the list of Blogs this user has write privileges on
  blogs = service.blogs()
  if debug: print 'blogs =',blogs
  request = blogs.listByUser(userId='self')
  if debug: print 'blogs().listByUser(userId="self") =',request.to_json()
  response = request.execute()
  if debug: print 'response =',json.dumps(response,indent=2)
  if 'items' in response:
    for blog in response['items']:
      if debug: print 'blog =',json.dumps(blog,indent=2)
      print 'The blog named \'%s\' is at: %s' % (blog['name'], blog['url'])
  else: print 'No blogs found'


def listPosts(args, debug=False):
  """
  Lists posts at blog.
  """
  service, http = authenticate(args)

  # Retrieve the list of Blogs this user has write privileges on
  blogs = service.blogs()
  if debug: print 'blogs =',blogs

  # Find blog by URL
  request = blogs.getByUrl(url=args.url)
  if debug: print 'blogs.getByUrl(url=args.url) =',request.to_json()
  response = request.execute()
  if debug: print 'response =',json.dumps(response, indent=2)
  #response = blogs.getByUrl(url=args.url).execute()
  id = response['id']
  if debug: print 'blogId =',id

  # Options
  status = None
  if args.draft: status = 'draft'
  if args.scheduled: status = 'scheduled'

  # Get list of posts
  posts = service.posts()
  if debug: print 'posts =',posts
  request = posts.list(blogId=id, status=status)
  if debug: print 'posts().list(blogId=id) =',request.to_json()
  response = request.execute()
  #response = service.posts().list(blogId=id).execute()
  if debug: print 'response =',json.dumps(response, indent=2)
  while 'items' in response:
    for item in response['items']:
      print item['published'],item['title']
      if debug: print json.dumps(item, indent=2)
    if 'nextPageToken' in response:
      request = posts.list(blogId=id, pageToken=response['nextPageToken'], status=status)
      response = request.execute()
    else:
      response = {} # Leave while loop


def authenticate(args, debug=False):
  """
  Handles authentication.

  Returns service object, Http object.
  """

  # Create storage for credentials
  storage = Storage('credentials.dat')
  if debug: print 'storage =',storage

  # Set up a Flow object to be used for authentication
  client_secrets = os.path.join(os.path.dirname(__file__),'client_secrets.json')
  flow = client.flow_from_clientsecrets(client_secrets,
      scope='https://www.googleapis.com/auth/blogger',
      message='Eeek')
  if debug: print 'flow =',flow

  # Load credentials from Storage object, or run(flow)
  credentials = storage.get() # Returns None if no credentials found
  if debug: print 'credentials =',credentials
  if credentials is None or credentials.invalid:
    credentials = run_flow(flow, storage, flags=args)
    if debug: print '2:credentials =',credentials

  # Create an httplib2.Http object to handle our HTTP requests, and authorize it
  # using the credentials.authorize() function.
  http = httplib2.Http()
  http = credentials.authorize(http)
  if debug: print 'http =',http

  # Create a service object
  service = build('blogger', 'v3', http=http)
  if debug: print 'service =',service

  return service, http


# Invoke the top-level procedure
if __name__ == '__main__': main()
