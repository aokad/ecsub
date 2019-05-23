class colors:
    "\033[40m\033[1;30m  Gray         \033[0m"
    "\033[40m\033[1;31m  Light Red    \033[0m"
    "\033[40m\033[1;32m  Light Green  \033[0m"
    "\033[40m\033[1;33m  Yellow       \033[0m"
    "\033[47m\033[1;34m  Light Blue   \033[0m"
    "\033[40m\033[1;35m  Pink         \033[0m"
    "\033[40m\033[1;36m  Light Cyan   \033[0m"
    "\033[40m\033[1;37m  White        \033[0m"

    RED       = "\033[40m\033[091m"
    GREEN     = "\033[40m\033[092m"
    YELLOW    = "\033[40m\033[093m"
    BLUE      = "\033[40m\033[094m"
    MAGENTA   = "\033[40m\033[095m"
    CYAN      = "\033[40m\033[096m"
    R_BLACK   = "\033[40m\033[100m"
    R_RED     = "\033[40m\033[101m"
    R_GREEN   = "\033[40m\033[102m"
    R_BLUE    = "\033[40m\033[104m"
    R_MAGENTA = "\033[40m\033[105m"
    R_CYAN    = "\033[40m\033[106m"
    
    HEADER    = '\033[95m'
    OKBLUE    = '\033[94m'
    OKGREEN   = '\033[92m'
    WARNING   = '\033[93m'
    FAIL      = '\033[91m'
    
    roll_list = [GREEN, YELLOW, MAGENTA, CYAN, R_BLACK, R_GREEN, R_BLUE, R_MAGENTA, R_CYAN, BLUE]
    
    @staticmethod
    def paint(text, color):
        return color + text + "\033[0m"  

if __name__ == "__main__":
    print (colors.paint("RED      ", colors.RED      ))
    print (colors.paint("GREEN    ", colors.GREEN    ))
    print (colors.paint("YELLOW   ", colors.YELLOW   ))
    print (colors.paint("BLUE     ", colors.BLUE     ))
    print (colors.paint("MAGENTA  ", colors.MAGENTA  ))
    print (colors.paint("CYAN     ", colors.CYAN     ))
    print (colors.paint("R_BLACK  ", colors.R_BLACK  ))
    print (colors.paint("R_RED    ", colors.R_RED    ))
    print (colors.paint("R_GREEN  ", colors.R_GREEN  ))
    print (colors.paint("R_BLUE   ", colors.R_BLUE   ))
    print (colors.paint("R_MAGENTA", colors.R_MAGENTA))
    print (colors.paint("R_CYAN   ", colors.R_CYAN   ))
    print (colors.paint("HEADER   ", colors.HEADER   ))
    print (colors.paint("OKBLUE   ", colors.OKBLUE   ))
    print (colors.paint("OKGREEN  ", colors.OKGREEN  ))
    print (colors.paint("WARNING  ", colors.WARNING  ))
    print (colors.paint("FAIL     ", colors.FAIL     ))
