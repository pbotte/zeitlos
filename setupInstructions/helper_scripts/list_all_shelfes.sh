#!/bin/bash

timeout 1 mosquitto_sub -t +/+/scales/+/mass -v > temp.txt

# Process each line of the input file
while IFS= read -r line
do
  # Extract the text between the first and the second "/"
  echo "$line" | cut -d'/' -f2 >> temp2.txt
done < temp.txt

cat temp2.txt | sort -u

rm -f temp2.txt temp.txt
