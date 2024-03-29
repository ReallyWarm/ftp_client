Socket Programming: FTP Client
โปรแกรมนี้ถูกพัฒนาขึ้นเพื่อเลียนแบบคำสั่ง ftp ในระบบปฏิบัติการ Windows ด้วยการใช้ socket library ในภาษา Python

โครงสร้างหลักของโปรแกรมสามารถทำงานแบบ Read-Evaluate-Print-Loop (REPL) และรับคำสั่งได้ ดังนี้
    •ascii(2 คะแนน)
    •binary(2 คะแนน)
    •bye(1 คะแนน)
    •cd(2 คะแนน)
    •close(1 คะแนน)
    •delete(2 คะแนน)
    •disconnect(1 คะแนน)
    •get(2 คะแนน)
    •ls(2 คะแนน)
    •open(2 คะแนน)
    •put(2 คะแนน)
    •pwd(2 คะแนน)
    •quit(1 คะแนน)
    •rename(2 คะแนน)
    •user(2 คะแนน)

เริ่มต้นการทำงานด้วยการสร้าง class FTPClient และเรียกใช้ method ชื่อ start

* หมายเหตุ: 
  มีการใช้ inspect (build-in libary) เพื่อใช้ตรวจสอบว่า user input เป็น method ของ FTPClient ที่นำไปใช้งานได้
  มีการใช้ time (build-in libary) เพื่อใช้คำนวนหาค่า transfer rate