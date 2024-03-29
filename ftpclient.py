import socket, inspect, time

class FTPClient():
    def __init__(self):
        self.ftp_socket = None
        self.current_host = None
        self.running = False

    def start(self):
        self.running = True
        invalid_commands = (FTPClient.start, FTPClient.clear_variable, FTPClient.get_host_from_pasv, 
                            FTPClient.is_connected, FTPClient.is_command_success, FTPClient.is_login_success, 
                            FTPClient.receive_all, FTPClient.peek_resp)
        while self.running:
            args = input("ftp> ").strip().split(" ")
            command = getattr(FTPClient, args[0].lower(), None)

            not_command = not inspect.isfunction(command)
            is_invalid = command in invalid_commands
            
            if args[0] == '':
                pass
            elif not_command or is_invalid:
                print("Invalid command.")
            else:
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
    
    def receive_all(self, sock, buff_size=4096):
        all_data = b''
        while True:
            data = sock.recv(buff_size)
            resp = data.decode()
            print(resp, end='')
            all_data += data
            if data == b'':
                break
            elif len(data) < buff_size:
                if len(data) >= 6:
                    if resp[0:3].isnumeric() and resp[3] == ' ':
                        break
                else:
                    break

        return all_data
    
    def peek_resp(self, sock, buff_size=4096):
        try:
            sock.setblocking(False)
            resp = sock.recv(buff_size, socket.MSG_PEEK)
            return resp
        except BlockingIOError:
            return b'BlockingIOError'
        except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
            return b''
        finally:
            sock.setblocking(True)
        

    def is_connected(self):
        if self.ftp_socket is None:
            return False
        
        close = False
        peek = self.peek_resp(self.ftp_socket, 5)
        if peek == b'':
            close = True
        elif peek.startswith((b'421', b'426', b'550')):
            self.receive_all(self.ftp_socket, 4096)
            close = True
        
        if close:
            self.ftp_socket.close() 
            self.clear_variable()
            return False
        
        return True

    def is_command_success(self):
        resp = self.receive_all(self.ftp_socket, 4096)
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

    def open(self, host=None, port=21, *_):
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
        self.receive_all(self.ftp_socket, 4096)
        self.ftp_socket.send("OPTS UTF8 ON\r\n".encode())
        self.receive_all(self.ftp_socket, 4096)

        username = input(f"User ({host}:(none)): ")
        self.ftp_socket.send(f"USER {username}\r\n".encode())
        if not self.is_login_success():
            return

        password = input("Password: ")
        self.ftp_socket.send(f"PASS {password}\r\n".encode())
        if not self.is_login_success():
            return

    def disconnect(self, *_):
        # Disconnect from the remote host, retaining the ftp prompt.
        if not self.is_connected():
            print("Not connected.")
            return
        
        self.ftp_socket.send(f'QUIT\r\n'.encode())
        self.receive_all(self.ftp_socket, 4096)
        self.ftp_socket.close()       
        self.clear_variable()

    def close(self, *_):
        # End the FTP session and return to the cmd prompt.
        self.disconnect()

    def quit(self, *_):
        # End the FTP session with the remote host and exit ftp.
        if self.is_connected():   
            self.ftp_socket.send(f'QUIT\r\n'.encode())
            self.receive_all(self.ftp_socket, 4096)
            self.ftp_socket.close()
            self.clear_variable
        else:
            print()
        self.running = False

    def bye(self, *_):
        # End the FTP session and exit ftp
        self.quit()

    def ascii(self, *args):
        # Set the file transfer type to ASCII, the default. 
        # In ASCII text mode, character-set and end-of-line
        # characters are converted as necessary.
        self.receive_all(self.ftp_socket, 4096)

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
        self.receive_all(self.ftp_socket, 4096)

    def delete(self, *args):
        pass

    def get(self, *args):
        pass

    def ls(self, rdir='', *_):
        if not self.is_connected():
            print("Not connected.")
            return
        
        host, port = self.get_host_from_pasv()
        self.ftp_socket.send(f"NLST {rdir}\r\n".encode())
        list_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        list_socket.connect((host, port))
        if not self.is_command_success():
            list_socket.close()
            return

        start_t = time.time()
        resp = self.receive_all(list_socket, 4096)
        elapsed = time.time() - start_t
        if elapsed == 0: elapsed = 0.000000001
        list_socket.close()

        self.receive_all(self.ftp_socket, 4096)
        resp_size = len(resp) + 3
        tf_rate = (resp_size/1000)/elapsed
        if tf_rate > resp_size: tf_rate = resp_size
        print(f"ftp: {resp_size} bytes received in {elapsed:.2f}Seconds {tf_rate:.2f}Kbytes/sec.")

    def put(self, *args):
        pass

    def pwd(self, *args):
        print()

    def rename(self, *args):
        pass

    def user(self, *args):
        pass