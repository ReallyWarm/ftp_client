Socket Programming: FTP Client
โปรแกรมนี้ถูกพัฒนาขึ้นเพื่อเลียนแบบคำสั่ง ftp ในระบบปฏิบัติการ Windows ด้วยการใช้ socket library ในภาษา Python

โครงสร้างหลักของโปรแกรมสามารถทำงานแบบ Read-Evaluate-Print-Loop (REPL) และรับคำสั่งได้ ดังนี้
    •ascii
    •binary
    •bye
    •cd
    •close
    •delete
    •disconnect
    •get
    •ls
    •open
    •put
    •pwd
    •quit
    •rename
    •user

สามารถรันไฟล์ myftp.py เพื่อเริ่มการทำงานของโปรแกรมได้
เริ่มต้นการทำงานด้วยการสร้าง class FTPClient และเรียกใช้ method ชื่อ start
class FTPClient จะอยู่ไฟล์ ftpclient.py

* หมายเหตุ: 
  มีการใช้ inspect (build-in libary) เพื่อใช้ตรวจสอบว่า user input เป็น method ของ FTPClient ที่นำไปใช้งานได้
  มีการใช้ time (build-in libary) เพื่อใช้คำนวนหาค่า transfer rate