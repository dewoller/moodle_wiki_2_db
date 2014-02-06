from bs4 import BeautifulSoup

# where so_soup.txt is your html
f = open ("/tmp/try.html", "r")
data = f.readlines ()
f.close ()

soup = BeautifulSoup ("".join (data))

print "User"
cells = soup.findAll('div', {"class" : "wiki_diffuserleft"})
for cell in cells:
    print (cell.get_text())

print "\nDeleted"
cells = soup.findAll('span', {"class" : "ouw_deleted"})
for cell in cells:
    print (cell.string)

print "\nAdded"
cells = soup.findAll('span', {"class" : "ouw_added"})
for cell in cells:
    print (cell.string)
