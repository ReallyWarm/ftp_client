import socket, inspect, time

class FTPClient():
    def __init__(self):
        self.ftp_socket = None
        self.server_name = None
        self.server_addr = None
        self.server_port = None
        self.my_addr = None
        self.my_port = None
        self.running = False

    def start(self):
        self.running = True
        invalid_commands = (FTPClient.start, FTPClient.clear_variable, FTPClient.receive_all, 
                            FTPClient.peek_resp, FTPClient.get_open_port, FTPClient.get_data_socket, 
                            FTPClient.attempt_connect, FTPClient.is_connected, FTPClient.is_command_success, 
                            FTPClient.is_login_success)
        
        while self.running:
            args = input("ftp> ").strip().split()
            if len(args) > 0:
                command = getattr(FTPClient, args[0].lower(), None)

                not_command = not inspect.isfunction(command)
                is_invalid = command in invalid_commands
                
                if not_command or is_invalid:
                    print("Invalid command.")
                else:
                    command(self, *args[1:])

    def clear_variable(self):
        self.ftp_socket = None
        self.server_name = None
        self.server_addr = None
        self.server_port = None
        self.my_addr = None
        self.my_port = None
    
    def receive_all(self, sock, buff_size=4096, is_data=False, show=True):
        all_data = b''
        while True:
            data = sock.recv(buff_size)
            all_data += data

            if data == b'':
                break
            elif len(data) < buff_size:
                new_resp_list = [d for d in data.split(b'\r\n') if d != b'']

                if len(new_resp_list[-1]) >= 4 and not is_data:
                    last_resp = new_resp_list[-1].decode()
                    if last_resp[0:3].isnumeric() and last_resp[3] == ' ':
                        break
        
        if show:
            print(all_data.replace(b'\r\n\r\n', b'\r\n').decode(), end='')
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

    def get_open_port(self):
        tmp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tmp_sock.bind(('', 0))
        port = tmp_sock.getsockname()[1]
        tmp_sock.close()
        return port

    def get_data_socket(self):
        port = self.get_open_port()
        addr_data = f"{self.my_addr}.{port//256}.{port%256}".replace('.',',')
        self.ftp_socket.send(f"PORT {addr_data}\r\n".encode())
        resp = self.receive_all(self.ftp_socket, 1024)
        if not resp.startswith(b'200'):
            return None
        
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            data_socket.bind((self.my_addr, port))
            return data_socket
        except socket.error as msg:
            print(f"Failed to connect: {msg}")
            return None

    def attempt_connect(self, sock, host, port):
        try:
            sock.connect((host, port))
            return True
        except socket.gaierror:
            print(f"Unknown host {host}.")
            return False
        except ConnectionRefusedError:
            print(f"> ftp: connect :Connection refused")
            return False
        except socket.error as msg:
            print(f"Failed to connect: {msg}")
            return False

    def is_connected(self, show_status=True):
        if self.ftp_socket is None:
            if show_status: print("Not connected.")
            return False
        
        close = False
        peek = self.peek_resp(self.ftp_socket, 5)
        if peek == b'':
            if show_status: print("Not connected.")
            close = True
        elif peek.startswith((b'421', b'425', b'426', b'550')):
            self.receive_all(self.ftp_socket, 4096)
            if show_status: print("Connection closed by remote host.")
            close = True
        
        if close:
            self.ftp_socket.close() 
            self.clear_variable()
            return False
        
        return True

    def is_command_success(self):
        resp = self.receive_all(self.ftp_socket, 4096)
        if resp.startswith((b'4', b'5')):
            return False
        return True
    
    def is_login_success(self):
        if not self.is_connected():
            return False
        
        if not self.is_command_success():
            print("Login failed.")
            return False
        return True

    def open(self, host=None, port=21, *_):
        if self.server_name:
            print(f"Already connected to {self.server_name}, use disconnect first.")
            return

        if host is None:
            host = input("To ")
        port = int(port)
        self.ftp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connected = self.attempt_connect(self.ftp_socket, host, port)
        if not connected:
            self.ftp_socket.close() 
            self.clear_variable()
            return
        
        self.my_addr, self.my_port = self.ftp_socket.getsockname()
        self.server_addr, self.server_port = self.ftp_socket.getpeername()
        if host == "127.0.0.1":
            self.server_name = "127.0.0.1"
        else:
            try:
                self.server_name = socket.gethostbyaddr(self.ftp_socket.getpeername()[0])[0]
            except socket.herror:
                self.server_name = host

        print(f"Connected to {self.server_name}.")
        self.receive_all(self.ftp_socket, 4096)
        self.ftp_socket.send("OPTS UTF8 ON\r\n".encode())
        self.receive_all(self.ftp_socket, 4096)

        username = input(f"User ({self.server_name}:(none)): ").strip()
        self.ftp_socket.send(f"USER {username}\r\n".encode())
        if not self.is_login_success():
            return

        password = input("Password: ").strip()
        self.ftp_socket.send(f"PASS {password}\r\n".encode())
        if not self.is_login_success():
            return

    def disconnect(self, *_):
        if not self.is_connected(show_status=False):
            return
        
        self.ftp_socket.send(f'QUIT\r\n'.encode())
        self.receive_all(self.ftp_socket, 4096)
        self.ftp_socket.close()       
        self.clear_variable()

    def close(self, *_):
        self.disconnect()

    def quit(self, *_):
        if self.is_connected(show_status=False):   
            self.ftp_socket.send(f'QUIT\r\n'.encode())
            self.receive_all(self.ftp_socket, 4096)
            self.ftp_socket.close()
            self.clear_variable
        
        self.running = False

    def bye(self, *_):
        self.quit()

    def ascii(self, *_):
        if not self.is_connected():
            return
        
        self.ftp_socket.send(f"TYPE A\r\n".encode())
        self.receive_all(self.ftp_socket, 4096)

    def binary(self, *_):
        if not self.is_connected():
            return
        
        self.ftp_socket.send(f"TYPE I\r\n".encode())
        self.receive_all(self.ftp_socket, 4096)

    def cd(self, rdir=None, *_):
        if not self.is_connected():
            return
        
        if rdir is None:
            rdir = input("Remote directory ")
        if rdir == '':
            print("cd remote directory.")
            return
        
        rdir = rdir.split()[0]
        self.ftp_socket.send(f"CWD {rdir}\r\n".encode())
        self.receive_all(self.ftp_socket, 4096)

    def delete(self, rfile=None, *_):
        if not self.is_connected():
            return
        
        if rfile is None:
            rfile = input("Remote file ")
        if rfile == '':
            print("delete remote file.")
            return
        
        rfile = rfile.split()[0]
        self.ftp_socket.send(f"DELE {rfile}\r\n".encode())
        self.receive_all(self.ftp_socket, 4096)

    def get(self, rfile=None, lfile=None, *_):
        if not self.is_connected():
            return
        
        if lfile is None:
            lfile = rfile

        if rfile is None:
            rfile = input("Local file ")
        if rfile == '':
            print("Local file put: remote file.")
            return
        tmp_info = rfile.split()
        rfile = tmp_info[0]

        if len(tmp_info) > 1:
            lfile = tmp_info[1]
        if lfile == None:
            lfile = input("Remote file ")
            if lfile == '':
                lfile = rfile.split('/')[-1]
            else:
                lfile = lfile.split()[0]

        with self.get_data_socket() as data_socket:
            if data_socket is None:
                return
            data_socket.listen()

            self.ftp_socket.send(f"RETR {rfile}\r\n".encode())
            if not self.is_command_success():
                return
            
            file = None
            try:
                file = open(lfile, 'wb')
            except FileNotFoundError:
                print("> R:No such process")
            except PermissionError:
                print(f"Error opening local file {lfile}.")
                return
            except Exception as msg:
                print(msg)
                return

            data_size = 0
            start_t = time.time()
            connection, _ = data_socket.accept()
            
            while True:
                data = connection.recv(4096)
                if data == b'' or data == '':
                    break
                if file is not None:
                    file.write(data)
                data_size += len(data)
            connection.close()

        self.receive_all(self.ftp_socket, 4096)
        file.close()

        elapsed = time.time() - start_t
        if elapsed == 0: elapsed = 0.000000001
        tf_rate = (data_size/1000)/elapsed
        if tf_rate > data_size: tf_rate = data_size
        print(f"ftp: {data_size} bytes received in {elapsed:.2f}Seconds {tf_rate:.2f}Kbytes/sec.")

    def ls(self, rdir='', *_):
        if not self.is_connected():
            return
        
        with self.get_data_socket() as data_socket:
            if data_socket is None:
                return
            data_socket.listen()
        
            self.ftp_socket.send(f"NLST {rdir}\r\n".encode())
            if not self.is_command_success():
                return
            
            start_t = time.time()
            connection, _ = data_socket.accept()
            resp = self.receive_all(connection, 4096, is_data=True)
            connection.close()

        self.receive_all(self.ftp_socket, 4096)
        elapsed = time.time() - start_t
        if elapsed == 0: elapsed = 0.000000001
        resp_size = len(resp) + 3
        tf_rate = (resp_size/1000)/elapsed
        if tf_rate > resp_size: tf_rate = resp_size
        print(f"ftp: {resp_size} bytes received in {elapsed:.2f}Seconds {tf_rate:.2f}Kbytes/sec.")

    def put(self, lfile=None, rfile=None, *_):
        if not self.is_connected():
            return
        
        if rfile is None:
            rfile = lfile

        if lfile is None:
            lfile = input("Local file ")
            if lfile == '':
                print("Local file put: remote file.")
                return
        tmp_info = lfile.split()
        lfile = tmp_info[0]

        if len(tmp_info) > 1:
            rfile = tmp_info[1]
        if rfile is None:
            rfile = input("Remote file ")
            if rfile == '':
                rfile = lfile.split('/')[-1]
            else:
                rfile = rfile.split()[0]

        try:
            file = open(lfile, 'rb')
        except FileNotFoundError:
            print(f"{lfile}: File not found")
            return
        except PermissionError:
            print(f"Error opening local file {lfile}.")
            return
        except Exception as msg:
            print(msg)
            return
        
        with self.get_data_socket() as data_socket:
            if data_socket is None:
                return
            data_socket.listen()

            self.ftp_socket.send(f"STOR {rfile}\r\n".encode())
            if not self.is_command_success():
                return
            
            data_size = 0
            start_t = time.time()
            connection, _ = data_socket.accept()
            
            while True:
                buffer = file.read(4096)
                if buffer == b'':
                    break
                connection.send(buffer)
                data_size += len(buffer)
            connection.close()

        self.receive_all(self.ftp_socket, 4096)
        elapsed = time.time() - start_t
        if elapsed == 0: elapsed = 0.000000001
        tf_rate = (data_size/1000)/elapsed
        if tf_rate > data_size: tf_rate = data_size
        print(f"ftp: {data_size} bytes received in {elapsed:.2f}Seconds {tf_rate:.2f}Kbytes/sec.")

    def pwd(self):
        if not self.is_connected():
            return
        
        self.ftp_socket.send(f"PWD\r\n".encode())
        if not self.is_command_success():
            return

    def rename(self, fromname=None, toname=None, *_):
        if not self.is_connected():
            return
        
        if fromname is None:
            fromname = input("From name ")
        if fromname == '':
            print("rename from-name to-name.")
            return
        
        rename_info = fromname.split()
        if len(rename_info) >= 2:
            toname = rename_info[1]
        if toname is None:
            toname = input("To name ")
        if toname == '':
            print("rename from-name to-name.")
            return
        
        fromname = rename_info[0]
        self.ftp_socket.send(f"RNFR {fromname}\r\n".encode())
        if not self.is_command_success():
            return
        
        self.ftp_socket.send(f"RNTO {toname}\r\n".encode())
        if not self.is_command_success():
            return

    def user(self, user=None, password=None, *_):
        if not self.is_connected():
            return

        if user is None:
            user = input("Username ").strip()
        if user == '':
            print("Usage: user username [password] [account]")
            return
        user_info = user.split()
        self.ftp_socket.send(f"USER {user_info[0]}\r\n".encode())
        if not self.is_login_success():
            return
        
        if len(user_info) >= 2:
            password = user_info[1]
        if password is None:
            password = input("Password: ").strip()
        self.ftp_socket.send(f"PASS {password}\r\n".encode())
        if not self.is_login_success():
            return