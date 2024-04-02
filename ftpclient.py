import socket, inspect, time

class FTPClient():
    TYPE_I = 'BINARY'
    TYPE_A = "ASCII"

    def __init__(self):
        self.ftp_socket = None
        self.server_name = None
        self.server_addr = None
        self.server_port = None
        self.my_addr = None
        self.my_port = None
        self.tf_mode = self.TYPE_I
        self.running = False

    def start(self):
        self.running = True
        invalid_commands = (FTPClient.start, FTPClient.clear_variable, FTPClient.receive_resp, 
                            FTPClient.peek_resp, FTPClient.get_open_port, FTPClient.get_data_socket, 
                            FTPClient.attempt_connect, FTPClient.is_connected, FTPClient.send_command,
                            FTPClient.is_command_success, FTPClient.show_transfer_rate)
        
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
        self.tf_mode = self.TYPE_I

    def receive_resp(self, sock, buff_size=4096, show=True):
        all_data = b''

        while True:
            data = sock.recv(buff_size)
            all_data += data

            if data == b'':
                break

            if all_data[3:4] == b'-':
                code = all_data[:3]
            else:
                break

            last_resp = [d for d in data.replace(b'\r', b'\n').split(b'\n') if d != b''][-1]
            if last_resp[:3] == code and last_resp[3:4] != b'-':
                break
        
        if show:
            print('\n'.join(d for d in all_data.decode().replace('\r', '\n').split('\n') if d != ''))
        return all_data
    
    def peek_resp(self, sock, buff_size=4096):
        try:
            sock.setblocking(False)
            resp = sock.recv(buff_size, socket.MSG_PEEK)
            return resp
        except BlockingIOError:
            return b'ALIVE'
        except ConnectionAbortedError:
            return b'426'
        except (ConnectionResetError, ConnectionError, socket.error):
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
        self.send_command(f"PORT {addr_data}")
        resp = self.receive_resp(self.ftp_socket, 1024)
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
            close = True
        elif peek.startswith((b'421', b'425', b'426', b'550')):
            self.receive_resp(self.ftp_socket, 4096)
            close = True
        
        if close:
            if show_status: print("Connection closed by remote host.")
            self.ftp_socket.close() 
            self.clear_variable()
            return False
        
        return True
    
    def send_command(self, command):
        if self.is_connected():
            self.ftp_socket.send((command + "\r\n").encode())

    def is_command_success(self):
        resp = self.receive_resp(self.ftp_socket, 4096)
        if resp.startswith((b'4', b'5')):
            return False
        return True
    
    def show_transfer_rate(self, start_time, end_time, size):
        elapsed = end_time - start_time
        if elapsed == 0: elapsed = 0.000000001
        tf_rate = (size/1000)/elapsed
        if tf_rate > size: tf_rate = size
        print(f"ftp: {size} bytes received in {elapsed:.2f}Seconds {tf_rate:.2f}Kbytes/sec.")

    def open(self, host=None, port=21, *_):
        if self.server_name:
            print(f"Already connected to {self.server_name}, use disconnect first.")
            return

        if host is None:
            host = input("To ")
            if host == '':
                print("Usage: open host name [port]")
                return
            else:
                tmp = host.split()
                host = tmp[0]
                if len(tmp) > 1:
                    port = tmp[1]
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
        self.receive_resp(self.ftp_socket, 4096)
        self.send_command("OPTS UTF8 ON")
        self.receive_resp(self.ftp_socket, 4096)

        username = input(f"User ({self.server_name}:(none)): ").strip()
        self.send_command(f"USER {username}")
        if not self.is_command_success():
            print("Login failed.")
            return

        password = input("Password: ").strip()
        self.send_command(f"PASS {password}")
        if not self.is_command_success():
            print("Login failed.")
            return

    def disconnect(self, *_):
        if not self.is_connected():
            return
        
        self.send_command(f"QUIT")
        self.receive_resp(self.ftp_socket, 4096)
        self.ftp_socket.close()       
        self.clear_variable()

    def close(self, *_):
        self.disconnect()

    def quit(self, *_):
        if self.is_connected(show_status=False):   
            self.send_command(f"QUIT")
            self.receive_resp(self.ftp_socket, 4096)
            self.ftp_socket.close()
            self.clear_variable
        
        self.running = False

    def bye(self, *_):
        self.quit()

    def ascii(self, *_):
        if not self.is_connected():
            return
        
        self.send_command(f"TYPE A")
        self.receive_resp(self.ftp_socket, 4096)
        self.tf_mode = self.TYPE_A

    def binary(self, *_):
        if not self.is_connected():
            return
        
        self.send_command(f"TYPE I")
        self.receive_resp(self.ftp_socket, 4096)
        self.tf_mode = self.TYPE_I

    def cd(self, rdir=None, *_):
        if not self.is_connected():
            return
        
        if rdir is None:
            rdir = input("Remote directory ")
        if rdir == '':
            print("cd remote directory.")
            return
        
        rdir = rdir.split()[0]
        self.send_command(f"CWD {rdir}")
        self.receive_resp(self.ftp_socket, 4096)

    def delete(self, rfile=None, *_):
        if not self.is_connected():
            return
        
        if rfile is None:
            rfile = input("Remote file ")
        if rfile == '':
            print("delete remote file.")
            return
        
        rfile = rfile.split()[0]
        self.send_command(f"DELE {rfile}")
        self.receive_resp(self.ftp_socket, 4096)

    def get(self, rfile=None, lfile=None, *_):
        if not self.is_connected():
            return
        
        if rfile is not None and lfile is None:
            lfile = rfile.split('/')[-1]

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
            
            file = None
            try:
                if self.tf_mode == self.TYPE_A:
                    file = open(lfile, 'w', encoding='utf-8', errors='replace')
                else:
                    file = open(lfile, 'wb')
            except FileNotFoundError:
                print("> R:No such process")
            except PermissionError:
                print(f"Error opening local file {lfile}.")
                return
            except Exception as msg:
                print(msg)
                return
            
            self.send_command(f"RETR {rfile}")
            if not self.is_command_success():
                return

            data_size = 0
            start_t = time.time()
            connection, _ = data_socket.accept()
            
            while True:
                data = connection.recv(4096)
                if data == b'':
                    break
                if file is not None:
                    if self.tf_mode == self.TYPE_A:
                        data = data.decode('utf-8', 'replace')
                        data = data.replace('\r\n', '\n').replace('\r', '\n')
                    file.write(data)
                data_size += len(data)
            connection.close()

        self.receive_resp(self.ftp_socket, 4096)
        if file is not None: file.close()
        end_t = time.time()
        self.show_transfer_rate(start_t, end_t, data_size)

    def ls(self, rdir='', *_):
        if not self.is_connected():
            return
        
        with self.get_data_socket() as data_socket:
            if data_socket is None:
                return
            data_socket.listen()
        
            self.send_command(f"NLST {rdir}")
            if not self.is_command_success():
                return
            
            data_size = 0
            start_t = time.time()
            connection, _ = data_socket.accept()

            while True:
                data = connection.recv(4096)
                if data == b'':
                    break
                print(data.decode(), end='')
                data_size += len(data)

            connection.close()

        self.receive_resp(self.ftp_socket, 4096)
        end_t = time.time()
        self.show_transfer_rate(start_t, end_t, data_size + 3)

    def put(self, lfile=None, rfile=None, *_):
        if not self.is_connected():
            return
        
        if lfile is not None and rfile is None:
            rfile = lfile.split('/')[-1]

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

            self.send_command(f"STOR {rfile}")
            if not self.is_command_success():
                return
            
            data_size = 0
            start_t = time.time()
            connection, _ = data_socket.accept()
            
            while True:
                buffer = file.readline(4096)
                if buffer == b'':
                    break
                if self.tf_mode == self.TYPE_A:
                    if buffer[-2:] != b'\r\n':
                        if buffer[-1] in b'\r\n': 
                            buffer = buffer[:-1]
                        buffer = buffer + b'\r\n'
                connection.send(buffer)
                data_size += len(buffer)
            connection.close()

        self.receive_resp(self.ftp_socket, 4096)
        file.close()
        end_t = time.time()
        self.show_transfer_rate(start_t, end_t, data_size)

    def pwd(self, *_):
        if not self.is_connected():
            return
        
        self.send_command(f"PWD")
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
        self.send_command(f"RNFR {fromname}")
        if not self.is_command_success():
            return
        
        self.send_command(f"RNTO {toname}")
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
        self.send_command(f"USER {user_info[0]}")
        if not self.is_command_success():
            print("Login failed.")
            return
        
        if len(user_info) >= 2:
            password = user_info[1]
        if password is None:
            password = input("Password: ").strip()
        self.send_command(f"PASS {password}")
        if not self.is_command_success():
            print("Login failed.")
            return