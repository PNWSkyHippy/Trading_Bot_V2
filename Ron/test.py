def calculate_distance_traveled(start_num, end_num):
    """ This function takes 2 numbers and returns the difference """
    if  (not isinstance(start_num, (int, float))) or (not isinstance(end_num, (int, float))):
        return None     #Non numeric argument sent
    elif  start_num  < 0 or end_num< 0:
       return None      #negative distance traveled sent 
    elif start_num == "" or end_num == "":
        return None   #redundannt would have been caught as a non int or float above
    else:
        return end_num - start_num
print(calculate_distance_traveled(5, -10000))