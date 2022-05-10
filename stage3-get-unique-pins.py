import sqlite3
import sys

DATABASE_PATH = "database.db"

def get_all_pins_url():
    returns = []
    cmd = "select pin_url from stage2"
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.execute(cmd)
            conn.commit()
            for i in cursor:
                returns.append(i[0])
    except:
        return get_all_pins_url()
    return returns

if __name__ == '__main__':
    file_out_path = 'output_of_third_tool.csv'
    try:
        for i in range(len(sys.argv)):
            if(sys.argv[i] == '-o'):
                file_out_path = sys.argv[i+1]
                break
    except:
        print("file_out_path is not set yet!")
    # input 
    links_pin = get_all_pins_url()
    
    
    # process
    pin_set = {}
    for i in links_pin:
        pin_set[i] = None

    print("There are ", len(pin_set), "unique urls/pins.")

    # output
    with open(file_out_path, "w") as f:
        for pin in pin_set:
            f.write(str(pin))
            f.write("\n") 