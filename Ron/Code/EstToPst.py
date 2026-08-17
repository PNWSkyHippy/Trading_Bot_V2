start_minutes = "01:32"

def Est_To_Pst(opening_minutes):
    hour = int(opening_minutes[:2])
    if (hour - 3) <= 0:
        mod_hour = 24 + (hour - 3)
    else:
        mod_hour = hour - 3
    hour_str = ""
    if mod_hour < 10:
        hour_str = "0{mod_hour}"
    else:
        hour_str = str(mod_hour)
    return(opening_minutes.replace(opening_minutes[:2], hour_str))


def main():
  conv_time = Est_To_Pst(start_minutes)
  print(f'Old time: {start_minutes}') 
  print(f'New Time: {conv_time}')

if __name__ == "__main__":
    main()
    