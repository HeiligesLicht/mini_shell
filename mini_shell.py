import lexer as ssp
import os, sys, signal, time, re
jobS =  []

def kill_pipes(pipes):
    for rfd, wfd in pipes:
        os.close(rfd)
        os.close(wfd)

def setup_redir(process):
    if process._redirs is not None:
        
        for redir in process._redirs._redirs:
            
            filename = redir.getFileSpec()

            if redir.isAppend():
                options = os.O_WRONLY | os.O_APPEND
            else:
                options = os.O_WRONLY | os.O_CREAT | os.O_TRUNC

            if isinstance(redir, ssp.OUTREDIR):
                fd = os.open(filename, flags=options)
                os.dup2(fd, 1)
                os.close(fd)
            elif isinstance(redir, ssp.ERRREDIR):
                fd = os.open(filename, flags=options)
                os.dup2(fd, 2)
                os.close(fd)
            else:
                fd = os.open(filename, flags=(os.O_WRONLY))
                os.dup2(fd, 0)
                os.close(fd)

def setup_pipeline(process, rfd, wfd, target, execute=True):
    os.close(rfd)
    os.dup2(wfd, target)
    setup_redir(process)
    if execute:
        sys.stdout.flush()
        sys.stdin.flush()
        os.execvp(process._cmd.getCommand(), [process._cmd.getCommand()] + process._cmd.getArgs())

def ctrl_z(sig, frame):
    global chld, jobS
    n = jobS.index([chld, "running"])
    jobS[n][1] = "stop"
    print()
    os.kill(chld, signal.SIGSTOP)

def ctrl_c(sig, frame):
    global chld
    global ppid
    if chld is not None:
        print("SIGINT Signal Received. Interrupting current job... Process ID: {} is exiting.".format(chld))
        os.kill(chld, signal.SIGTERM)
    else:
        print("\nmini-shell is interrupted by SIGINT Signal. Process ID: {} is exiting.".format(ppid))
        print("Hasta la vista, baby.")
        os.kill(ppid, signal.SIGTERM)


def jobs():
    global jobS
    for key, value in jobS:
        print(str(key), "---> " + value)

def bg(num = 0):
    global jobS
    jobS[num][1] = "running"
    os.kill(jobS[num][0], signal.SIGCONT)

def fg(num = 0):
    global jobS, chld
    pid = os.fork()
    if pid == 0:
        os.tcsetpgrp(1, os.getpgid(os.getpid()))
    else:
        chld = pid
        jobS[num] = [chld, "running"]
        os.setpgid(pid, 0)
        os.kill(jobS[num][0], signal.SIGCONT)
        signal.pause() 

ctrl_quit = ctrl_c


print("Bonjour, Hello, 你好, Здравствуйте, こんにちは.")

ppid = os.getpid()

while True:

    chld = None
    
    signal.signal(signal.SIGTTIN, signal.SIG_IGN)
    signal.signal(signal.SIGINT, ctrl_c)
    signal.signal(signal.SIGQUIT, ctrl_quit)
    signal.signal(signal.SIGTSTP, ctrl_z)
    
    

    raw_input = input("ʕ•ᴥ•ʔ > ")

    if raw_input == '':
        continue

    elif raw_input == 'jobs':
        jobs()
        continue

    elif raw_input[0:2] == 'fg':
        if len(raw_input) == 2:
            fg()
        else:
            fg(int(raw_input[4]))
        continue

    elif raw_input[0:2] == 'bg':
        if len(raw_input) == 2:
            bg()
        else:
            bg(int(raw_input[4]))
        continue

    else:
        processes = ssp.get_parser().parse(raw_input)

        pipe_tab = [os.pipe() for i in range(len(processes) - 1)]

        for i in range(len(processes)):
            pid = os.fork()
            
            if pid == 0:
                if i == 0:
                    if pipe_tab != []:
                        rfd, wfd = pipe_tab[0]
                    else:
                        rfd, wfd = 1, 0
                    setup_pipeline(processes[i], rfd, wfd, 1)
                elif i == len(processes) - 1:
                    rfd, wfd = pipe_tab[-1]
                    setup_pipeline(processes[i], wfd, rfd, 0)
                else:
                    rfd1, wfd1 = pipe_tab[i-1]
                    rfd2, wfd2 = pipe_tab[i]
                    setup_pipeline(processes[i], wfd1, rfd1, 0, execute=False)
                    setup_pipeline(processes[i], rfd2, wfd2, 1)
            else:
                chld = pid
                jobS.append([chld, "running"])
    
    kill_pipes(pipe_tab)

    for i in range(len(processes)):
        os.waitpid(-1,os.WUNTRACED)

    continue