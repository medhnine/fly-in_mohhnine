with open("/home/mohhnine/Desktop/fly-in/maps/hard/03_ultimate_challenge.txt", "r") as file:
    content = file.read()

with open("log.txt", "w") as file:
    file.write(content)
    file.write("\n".join(sim.visualizer.recordes))