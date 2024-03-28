import socket, inspect

class FTPClient():
    def __init__(self):
        self.ftp_socket = None
        self.current_host = None
        self.running = False

    def start(self):
        self.running = True
        while self.running:
            args = input("ftp> ").strip().split(" ")
            command = getattr(FTPClient, args[0].lower(), None)

            not_command = not inspect.isfunction(command)
            invalid_command = command == FTPClient.start or command == FTPClient.clear_variable or \
                              command == FTPClient.get_host_from_pasv or command == FTPClient.is_connected or \
                              command == FTPClient.is_command_success or command == FTPClient.is_login_success

            if not (not_command or invalid_command):
                command(self, *args[1:])

    def clear_variable(self):
        self.ftp_socket = None
        self.current_host = None

    def get_host_from_pasv(self):
        self.ftp_socket.send("PASV\r\n".encode())
        resp = self.ftp_socket.recv(1024)
        data = resp.decode().replace(')',',').replace('(',',').split(',')
        host = ".".join(data[1:5])
        port = int(data[5])*256+int(data[6])
        return host, port

    def is_connected(self):
        if self.ftp_socket is None:
            return False
        
        try:
            self.ftp_socket.setblocking(False)
            resp = self.ftp_socket.recv(1024, socket.MSG_PEEK)
            print(resp.decode(), end="")
            if resp == b'' or b'421':
                self.ftp_socket.close() 
                self.clear_variable()
                return False
            else:
                self.ftp_socket.setblocking(True)
                return True
        except BlockingIOError:
            self.ftp_socket.setblocking(True)
            return True
        except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
            self.ftp_socket.close() 
            self.clear_variable()
            return False

    def is_command_success(self):
        resp = self.ftp_socket.recv(1024)
        print(resp.decode(), end="")
        if resp.startswith(b'5'):
            return False
        return True
    
    def is_login_success(self):
        if not self.is_connected():
            print("Connection closed by remote host.")
            return False
        
        if not self.is_command_success():
            print("Login failed.")
            return False
        return True

    def open(self, host=None, port=21, *args):
        if self.is_connected() and self.current_host:
            print(f"Already connected to {self.current_host}, use disconnect first.")
            return

        if host is None:
            host = input("To ")
        port = int(port)
        self.ftp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            print(f"Connecting to {host}.")
            self.ftp_socket.connect((host, port))
        except socket.gaierror:
            print(f"Unknown host {host}.")
            self.ftp_socket.close() 
            self.clear_variable()
            return
        except socket.error as msg:
            print(f"Failed to connect: {msg}")
            self.ftp_socket.close() 
            self.clear_variable()
            return
        
        self.current_host = host
        resp = self.ftp_socket.recv(1024)
        print(resp.decode(), end="")
        self.ftp_socket.send("OPTS UTF8 ON\r\n".encode())
        resp = self.ftp_socket.recv(1024)
        print(resp.decode(), end="")

        username = input(f"User ({host}:(none)): ")
        self.ftp_socket.send(f"USER {username}\r\n".encode())
        if not self.is_login_success():
            return

        password = input("Password: ")
        self.ftp_socket.send(f"PASS {password}\r\n".encode())
        if not self.is_login_success():
            return

    def disconnect(self, *args):
        # Disconnect from the remote host, retaining the ftp prompt.
        if not self.is_connected():
            print("Not connected.")
            return
        
        self.ftp_socket.send(f'QUIT\r\n'.encode())
        resp = self.ftp_socket.recv(1024)
        print(resp.decode(), end="")
        self.ftp_socket.close()       
        self.clear_variable()

    def close(self, *args):
        # End the FTP session and return to the cmd prompt.
        self.disconnect()

    def quit(self, *args):
        # End the FTP session with the remote host and exit ftp.
        if self.is_connected():   
            self.ftp_socket.send(f'QUIT\r\n'.encode())
            resp = self.ftp_socket.recv(1024)
            print(resp.decode())
            self.ftp_socket.close()
            self.clear_variable
        else:
            print()
        self.running = False

    def bye(self, *args):
        # End the FTP session and exit ftp
        self.quit()

    def ascii(self, *args):
        # Set the file transfer type to ASCII, the default. 
        # In ASCII text mode, character-set and end-of-line
        # characters are converted as necessary.
        pass

    def binary(self, *args):
        # Set the file transfer type to binary. 
        # Use `Binary' for transferring executable program
        # files or binary data files e.g. Oracle
        pass

    def cd(self, rdir=None, *args):
        if not self.is_connected():
            print("Not connected.")
            return
        
        if rdir is None:
            rdir = input(f"Remote directory ")
        
        self.ftp_socket.send(f"CWD {rdir}\r\n".encode())
        resp = self.ftp_socket.recv(1024)
        print(resp.decode(), end="")

    def delete(self, *args):
        pass

    def get(self, *args):
        pass

    def ls(self, rdir='', *args):
        if not self.is_connected():
            print("Not connected.")
            return
        
        host, port = self.get_host_from_pasv()
        list_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        list_socket.connect((host, port))
        self.ftp_socket.send(f"NLST {rdir}\r\n".encode())
        if not self.is_command_success():
            list_socket.close()
            return

        while True:
            list_data = list_socket.recv(4096)
            if not list_data:
                list_socket.close()
                break
            print(list_data.decode(), end='')

        resp = self.ftp_socket.recv(1024)
        print(resp.decode(), end="")

    def put(self, *args):
        pass

    def pwd(self, *args):
        print()

    def rename(self, *args):
        pass

    def user(self, *args):
        pass