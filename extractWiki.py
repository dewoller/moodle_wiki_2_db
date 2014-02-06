#!/usr/bin/python
# coding: utf-8
#whichWiki=4539
import re
import mechanize
import cookielib
from bs4 import BeautifulSoup
import os
import sqlite3 as lite
import time
import datetime
import logging
import sys

import argparse

parser = argparse.ArgumentParser(description='Extract diffs from a Moodle  wiki')
parser.add_argument('--wikiPage')
parser.add_argument('--db')
args = parser.parse_args(sys.argv[1:])
wikiPage=vars(args)['wikiPage']
dbfile=vars(args)['db']
#dbfile="/home/dewoller/bin/wikiContribution.db"
#import pdb; pdb.set_trace()


def setupdb():

    if os.access(dbfile, os.F_OK):
        return
    
    con = lite.connect(dbfile)
    cur = con.cursor()
    stmt = """PRAGMA encoding='UTF-8' """
    cur.execute(stmt)
    con.commit()
    stmt = """  create table diff (
                wikiID integer, 
                pageID integer,
                diffID integer,
                user text,
                additions text,
                deletions text,
                changeBlock text,
                fileContent text,
                url text,
                changeDate datetime,
                wordsAdded integer,
                wordsDeleted integer,
                primary key (wikiID, pageID, diffID)
                )
                """
    cur = con.cursor()
    cur.execute(stmt)
    con.commit()
    con.close()

def insertdb( wikiID, pageID, diffID, user, additions, deletions, changeBlock, fileContent, url, changeDate, wordsAdded, wordsDeleted ):

    con = lite.connect(dbfile)
    cur = con.cursor()
    stmt = """  
    insert into diff ( wikiID, pageID, diffID, user, additions, deletions, changeBlock, fileContent, url, changeDate, wordsAdded, wordsDeleted )
    values
    (?,?,?,?,?,?,?,?,?,?,?,?)
    """
    #cur.execute(stmt, ( wikiID, pageID, diffID, user, additions, deletions, fileContent, url, changeDate, wordsAdded, wordsDeleted ))
    cur.execute(stmt, ( 
        wikiID, 
        pageID, 
        diffID, 
        re.sub("'","", user), 
        additions.encode('ascii', 'ignore'), 
        deletions.encode('ascii', 'ignore'), 
        changeBlock.encode('ascii', 'ignore'), 
        fileContent.encode('ascii', 'ignore'), 
        url.encode('ascii', 'ignore'), 
        changeDate, 
        wordsAdded, 
        wordsDeleted 
        ))
    con.commit()
    con.close()

def getLastProcessedDiffID( wikiID, pageID):
#    return 1
    con = lite.connect(dbfile)
    cur = con.cursor()
    stmt = """  
    select max(diffID) from diff
        where wikiID=? and pageID=?
    """
    cur.execute(stmt, ( wikiID, pageID))
    if (cur == None  ):
        rv=0
    else:
        rv = (cur.fetchone())[0]
        if rv == None:
            rv = 0
    con.close()
    return rv;

def setup( br):

    # Browser options
    br.set_handle_equiv(True)
    br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)

    # Follows refresh 0 but not hangs on refresh > 0
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    # Want debugging messages?
    #br.set_debug_http(True)
    #br.set_debug_redirects(True)
    #br.set_debug_responses(True)

    # User-Agent (this is cheating, ok?)
    br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
    return 

def login(br):
    br.open("https://www.latrobe.edu.au/lms/login/")
    # follow second link with element text matching regular expression
    #response1 = br.follow_link(text_regex=r"cheese\s*shop", nr=1)
    assert br.viewing_html()
    logging.info( br.title())
    logging.info( br.geturl())
    # Show the available forms
    #for f in br.forms():
    #    logging.info( f)

    # Browser passes through unknown attributes (including methods)
    # to the selected HTMLForm.
    br.select_form(nr=0)
    br["username"] = "XXXXXX" 
    br["password"] = "XXXXXX" 
    br["domain"] = ["ltu.edu.au"]
    # Submit current form.  Browser calls .close() on the current response on
    # navigation, so this closes response1
    response2 = br.submit()
    #f=open("postlogin.html","w")
    #f.write(br.response().read())
    #f.close

def has_class_but_no_id(tag):
    return tag.has_key('class') and not tag.has_key('id')

def processWiki( wikiID ) :
    logging.info( "processing entire wiki %s" % wikiID)
    br.open("https://lms.latrobe.edu.au/mod/wiki/map.php?pageid=%s" % wikiID)
    soup = BeautifulSoup (br.response().read())
    cells = soup.findAll('tr', {"class" : re.compile("r[01]$")})
    #import pdb; pdb.set_trace()
    for cell in cells:
        pageRef =cell.find('a', href=re.compile("pageid"))
        if pageRef == None:
            continue
        pageID = re.search('pageid=(.*)', pageRef['href']).group(1)
        if pageID == None:
            continue
        pageID=str(pageID)
        logging.info( "processing pageID %s" % pageID )
        processWikiPage( wikiID, pageID)

def processWikiPage( wikiID, pageID) :
    startDiffID=getLastProcessedDiffID( wikiID, pageID)
    (pageName, maxDiffID)=getPageInfo( pageID )
    logging.info( 'wiki page # %s, name=%s, first diff= %d, last diff= %d' % (pageID, pageName, startDiffID, maxDiffID))
    if maxDiffID<0 or startDiffID >= maxDiffID:
        return
    for i in range(startDiffID+1, maxDiffID):
        processDiffPage( wikiID, pageName, pageID, i )

def getPageInfo( pageID ): 
    br.open("https://lms.latrobe.edu.au/mod/wiki/history.php?pageid=%s" % pageID )
    soup = BeautifulSoup (br.response().read())
    #import pdb; pdb.set_trace()
    cell = soup.findAll('span', {"class" : "radioelement compare rb0"})
    if (len(cell)==0):
        return ("",-1) 
    maxDiffID= int(re.search(r'"(\d+)"',str(cell[0].contents)).group(1))
    pageName=soup.findAll("h2", {"class" : "main help"})[0].getText()
    pageName = re.sub('[^a-zA-Z]+','_', pageName)
    return (pageName, maxDiffID)
    
def processDiffPage( wikiID, pageName, pageID, diffID) :
    logging.info( "processing diff wiki page %s, diff # %s " % (pageID, diffID))
    url="https://lms.latrobe.edu.au/mod/wiki/diff.php?pageid=%s&comparewith=%s&compare=%s" % (pageID, diffID+1, diffID) 
    logging.info( url)
    br.open( url )
    cj.save( ignore_discard=True )
    logging.info( br.geturl())
#    logging.info( br.response().read()  # body)
    storeChanges( wikiID, pageName, pageID, diffID, br.response().read(), url)    

def storeChanges(wikiID, pageName,  pageID, diffID, webpage, url):
    # todo
    # store in database
    # add in link to actual final document
    # add in date and time and size of edit in words and letters
    filename="diffWikiID_%s_%s_%s_DID%03d.html"% (wikiID, pageName, pageID,  diffID)
    f=open(filename,"w")
    f.write(webpage)
    f.close

    soup = BeautifulSoup (webpage)
    logging.info( "User: ",)
    #import pdb; pdb.set_trace()
    user = soup.findAll('div', {"class" : "wiki_diffuserright"})[0].get_text()
    logging.info( (user))

    logging.info( "Date: ",)
    changeDate = soup.findAll('div', {"class" : "wiki_difftime"})[1].get_text()
    logging.info( changeDate)
    #12 January 2013, 7:55 AM
    cdt=datetime.datetime.strptime(changeDate, "%d %B %Y, %H:%M %p")

    #import pdb; pdb.set_trace()
    logging.info( "\nChangeBlock")
    changeBlock=u"\n".join([ 
                unicode(soup.findAll('h2', {"class" : "wiki_headingtitle"})[0]),
                unicode(soup.findAll('h2', {"class" : "main"})[0]),
                unicode(soup.findAll('div', {"class" : "wiki-diff-container clearfix"})[0])
                ])
    logging.info(changeBlock)

    logging.info( "\nDeleted")
    deletedText=u"\n".join([ i.getText() for i in soup.findAll('span', {"class" : "ouw_deleted"})])
    logging.info(deletedText)

    logging.info( "\nAdded")
    addedText=u"\n".join([ i.getText() for i in soup.findAll('span', {"class" : "ouw_added"})])
    logging.info(addedText)
    logging.info( "_________________________________")
    insertdb( wikiID, pageID, diffID, user, addedText, deletedText, changeBlock, filename, url, cdt, 
            len(addedText.split()),
            len(deletedText.split())
            )


# Browser setup,start


def main():
    logging.basicConfig( level=logging.INFO)
    logging.info('Started')
    quickStart = True
    if quickStart and ( os.access(cookie_filename, os.F_OK) 
        and time.time() - 
            time.mktime(datetime.datetime.strptime(str(time.ctime(os.path.getmtime(cookie_filename))) , "%a %b %d %H:%M:%S %Y").timetuple())
                <3600
        ):
        cj.load( ignore_discard=True)
    else:
        logging.info( "Logging in")
        login( br )
        cj.save( ignore_discard=True )

    logging.info( "logged in")
    # get map page
    # for each page  in map
    processWiki( wikiPage )
    logging.info('Finished')

if __name__ == '__main__':
    br = mechanize.Browser()
    setup(br)
    setupdb()
    # Cookie Jar
    cookie_filename="/tmp/cookie.jar" 
    cj = cookielib.LWPCookieJar(cookie_filename)
    br.set_cookiejar(cj)
    main()

