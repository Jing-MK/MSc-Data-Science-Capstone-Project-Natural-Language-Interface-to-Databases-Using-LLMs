import sqlite3, os
os.path.exists("demo.sqlite") and os.remove("demo.sqlite")
c = sqlite3.connect("demo.sqlite"); cur = c.cursor()
cur.execute("""CREATE TABLE schools (
  CDSCode TEXT PRIMARY KEY, School TEXT, "School Name" TEXT, County TEXT, MailZip TEXT,
  AdmFName1 TEXT, AdmLName1 TEXT, AdmFName2 TEXT, AdmLName2 TEXT, FundingType TEXT, Charter INT)""")
cur.execute("""CREATE TABLE frpm (
  CDSCode TEXT, "Free Meal Count (K-12)" INT, "Enrollment (K-12)" INT,
  FOREIGN KEY(CDSCode) REFERENCES schools(CDSCode))""")
schools = [
 ("01-A","Alpha High","Alpha High School","Alameda","94501","Avetik","Atoian","Mary","Smith","Locally funded",1),
 ("01-B","Beta High","Beta High School","Alameda","94502","John","Doe",None,None,"Directly funded",1),
 ("01-C","Gamma Prep","Gamma Preparatory Academy","Alameda","94503","Avetik","Atoian",None,None,"Locally funded",1),
 ("02-A","Delta School","Delta Elementary School","Fresno","93701","Jane","Roe",None,None,"Directly funded",0),
]
frpm = [("01-A",120,400),("01-B",80,500),("01-C",60,300),("02-A",200,800)]
cur.executemany("INSERT INTO schools VALUES (?,?,?,?,?,?,?,?,?,?,?)", schools)
cur.executemany("INSERT INTO frpm VALUES (?,?,?)", frpm)
c.commit(); c.close(); print("demo.sqlite built (schools + frpm, FK linked)")
