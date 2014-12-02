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
# iPython notebooks
from IPython.nbconvert import HTMLExporter

def main():
  """
  Parse the command line positional and optional arguments.
  This is the highest level procedure that invokes the real workers.
  """
  global debug

  thisTool = 'ipynb2blogger.py'
  parser = argparse.ArgumentParser(
    description=thisTool+' is a tool for posting iPython notebooks to blogger.',
    parents=[argparser],
    epilog='Written by A.Adcroft, 2014 (https://github.com/Adcroft).')
  parser.add_argument('-d', '--debug', action='store_true', help='Turn on debugging.')
  parser.add_argument('url', type=str, nargs='?',
    help='URL of blogger blog. Only required for commands \'posts\' and \'post\'.')
  subparsers = parser.add_subparsers(prog=thisTool+' url')

  # These sub-commands do not need the url arguments so need a "prog=" argument to add_parser()
  parser_logIn = subparsers.add_parser('login', prog=thisTool+' login',
                   help='Log on to blogger.',
                   description='Authenticate with blogger. A browser will appear for you to login to google.')
  parser_logIn.set_defaults(action=logIn)

  msg = 'Disconnects the authenticated user.'
  parser_logOut = subparsers.add_parser('logout', prog=thisTool+' logout', help=msg, description=msg)
  parser_logOut.set_defaults(action=logOut)

  msg = 'Display the authenticated blogger user name.'
  parser_whoAmI = subparsers.add_parser('whoami', prog=thisTool+' whoami', help=msg, description=msg)
  parser_whoAmI.set_defaults(action=whoAmI)

  msg = 'Lists blogs that the authenticated user can post to.'
  parser_listBlogs = subparsers.add_parser('blogs', prog=thisTool+' blogs', help=msg, description=msg)
  parser_listBlogs.set_defaults(action=listBlogs)

  msg = 'Lists posts in blog at url.'
  parser_listPosts = subparsers.add_parser('posts', help=msg, description=msg)
  parser_listPosts.set_defaults(action=listPosts)
  group = parser_listPosts.add_mutually_exclusive_group()
  group.add_argument('-p', '--published', action='store_true', help='Only list published posts.')
  group.add_argument('-d', '--draft', action='store_true', help='Only list draft posts.')
  group.add_argument('-s', '--scheduled', action='store_true', help='Only list scheduled posts.')

  msg = 'Upload a post to blog at url.'
  parser_post = subparsers.add_parser('post', help=msg, description=msg)
  parser_post.add_argument('file', type=str, help='File to upload as the post.')
  parser_post.add_argument('-l', '--label', type=str, default=None,
    help='Label to attach to post. Repeat for multiple labels.', action='append')
  parser_post.add_argument('-t', '--title', type=str, default=None,
    help='Title to give the post. By default, the file name is used for the title.')
  parser_post.add_argument('-u', '--update', action='store_true',
    help='Update existing post matching this title. By default a matching post will block the new post to avoid accidentally overwriting posts.')
  parser_post.set_defaults(action=post)

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
  blogId = response['id']
  if debug: print 'blogId =',blogId

  # Options
  statuses = [None, 'draft', 'scheduled']
  if args.published: statuses = [None]
  if args.draft: statuses = ['draft']
  if args.scheduled: statuses = ['scheduled']

  # Get list of posts
  posts = service.posts()
  if debug: print 'posts =',posts

  for status in statuses:

    request = posts.list(blogId=blogId, status=status, fetchBodies=False)
    if debug: print 'posts().list(blogId=blogId) =',request.to_json()
    response = request.execute()
    #response = service.posts().list(blogId=blogId).execute()
    if debug: print 'response =',json.dumps(response, indent=2)
    while 'items' in response:
      for item in response['items']:
        if status is 'scheduled':
          print 'Sched',item['published'],item['title']
        elif status is 'draft':
          print 'Draft',item['published'],item['title']
        else:
          print '     ',item['published'],item['title']
        if debug: print json.dumps(item, indent=2)
      if 'nextPageToken' in response:
        request = posts.list(blogId=blogId, pageToken=response['nextPageToken'], status=status, fetchBodies=False)
        response = request.execute()
      else:
        response = {} # Leave while loop


def post(args, debug=False):
  """
  Inserts a file as a post to a blog.
  """

  title, suffix = os.path.splitext( os.path.basename(args.file) )

  # Need to add mathJax header in front of html
  mathJaxFile = os.path.join(os.path.dirname(__file__),'mathJax.html')
  with open (mathJaxFile, 'r') as htmlFile:
    mathJax = htmlFile.read()

  # Read file to post
  if suffix in ('.html','.htm'):
    with open (args.file, 'r') as htmlFile:
      html = mathJax + htmlFile.read()
  elif suffix in '.ipynb':
    exportHtml = HTMLExporter(template_file='basic')
    html = mathJax + exportHtml.from_filename(args.file)[0]
  else:
    print args.file,'has an unrecognized suffix. Stopping.'
    return

  # Labels for post
  if args.label is None: labels = None
  else: labels = args.label

  if args.title is not None: title = args.title

  # Start communications with blogger
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

  # Get blogId
  blogId = response['id']
  if debug: print 'blogId =',blogId

  # posts instance
  posts = service.posts()
  if debug: print 'posts =',posts

  # Build body of post

  # Check post doesn't already exist
  existingPost = getPostByTitle(posts, blogId, title, status='draft', debug=False)
  if existingPost == None:
    existingPost = getPostByTitle(posts, blogId, title, status='scheduled', debug=False)
  if existingPost == None:
    existingPost = getPostByTitle(posts, blogId, title, status='live', debug=False)

  if existingPost != None:
    if args.update:
      existingPost['content'] = html
      if labels != None: existingPost['labels'] = labels
      postId = existingPost['id']
      request = posts.update(blogId=blogId, postId=postId, body=existingPost)
      if debug: print 'posts().update() =',request.to_json()
      response = request.execute()
      if debug: print 'response =',json.dumps(response, indent=2)
    else:
      print 'Post "'+title+'" already exists!'
  else:
    # Insert new post
    body = {}
    body['kind'] = 'blogger#post'
    body['title'] = title
    body['content'] = html
    body['blog'] = {'id': blogId}
    body['labels'] = labels
    request = posts.insert(blogId=blogId, body=body, isDraft=True)
    if debug: print 'posts().insert() =',request.to_json()
    response = request.execute()
    if debug: print 'response =',json.dumps(response, indent=2)


def getPostByTitle(posts, blogId, title, status='draft', debug=False):
  """
  Searches through posts looking for a post with matching title.

  Returns post or None.
  """

  # Get list of posts
  request = posts.list(blogId=blogId, status=status, fetchBodies=False)
  if debug: print 'posts().list(blogId=blogId) =',request.to_json()
  response = request.execute()
  #response = posts.list(blogId=blogId).execute()
  if debug: print 'response =',json.dumps(response, indent=2)
  while 'items' in response:
    for item in response['items']:
      if title == item['title']:
        return item
      if debug: print json.dumps(item, indent=2)
    if 'nextPageToken' in response:
      request = posts.list(blogId=blogId, pageToken=response['nextPageToken'], status=status, fetchBodies=False)
      response = request.execute()
    else:
      response = {} # Leave while loop
  return None


def logIn(args, debug=False):
  """
  Authenticates user.
  """

  service, http = authenticate(args)


def logOut(args, debug=False):
  """
  Disconnects the authenticated user.
  """

  try:
    os.remove('.blogger.credentials')
  except:
    print 'No credentials file found! Are in the right directory or did you log off already?'


def authenticate(args, debug=False):
  """
  Handles authentication.

  Returns service object, Http object.
  """

  # Create storage for credentials
  storage = Storage('.blogger.credentials')
  if debug: print 'storage =',storage

  # Set up a Flow object to be used for authentication
  client_secrets = os.path.join(os.path.dirname(__file__),'client_secrets.json')
  flow = client.flow_from_clientsecrets(client_secrets,
      scope='https://www.googleapis.com/auth/blogger',
      message='Could not find a valid client_secrets.json file!')
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
