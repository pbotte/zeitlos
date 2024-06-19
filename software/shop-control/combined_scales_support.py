#Unterstützung für Doppelbreite Waagen

combined_scales_data_array = []

def load_combined_scales_config():
    global combined_scales_data_array
    with open('/home/pi/zeitlos/config/combined_scales', 'r') as file:
        for line in file:
            # Split the line by spaces to get individual elements
            elements = line.lower().split()
            # Append the elements to the data array
            combined_scales_data_array.append(elements)

# Function to search for the scaleid
# convert an string to an array of "connected" scales 
# eg '493037f73304' is found -> ['493037f73304', '493037f73305']
# eg '493037f73306' is not found -> ['493037f73306']
def search_scale_and_convert_to_array(target):
    for i, sublist in enumerate(combined_scales_data_array):
        if target.lower() in sublist:
            #print(f'The string "{target}" is found at index {i}')
            return combined_scales_data_array[i]
#    print(f'The string "{target}" is not found in the array')
    return [target]

load_combined_scales_config()

