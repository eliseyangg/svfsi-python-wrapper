import os
import sv
import vtk

#==============================================
# SETUP, FILL OUT INFORMATION BELOW

# CREATE A SIMVASCULAR PROJECT MANUALLY USING GUI

# FOLDER TO MESHES + SVFSI INPUT FILE
input_path = "/Users/elise/Desktop/research2022/wrappertest"
# SVFSI INPUT FILE NAME
svfsi_inp = "svfsi.inp"
# if model needs to be imported, set to false. if model is already loaded into a project, set to true
loaded_on_gui = False
# MODEL FILE PATH if needs to be imported
model_path = "/Users/elise/Desktop/research2022/practice/SVProject/demo.stl"
# MODEL NAME (NEEDS TO BE SAME AS MESH WRITTEN IN SVFSI INPUT FILE)
model_name = "demo"

# global edge size must match remesh size resolution. see if there is code to get estimate remesh size
edge_size = 0.2
# FACE IDS FOR THE WALLS check model. see if there is code to get this
wall_face_ids = [1,2] 

# SVFSI PATH
svfsi_path = "/Users/elise/sv/svFSI_build/svFSI-build/bin/svFSI"

#perhaps add another option how many times to remesh

#==============================================

os.chdir(input_path)

if loaded_on_gui == False:
    # create modeler for polydata kernel
    modeler = sv.modeling.Modeler(sv.modeling.Kernel.POLYDATA)
    model = modeler.read(model_path)
    sv.dmg.add_model(model_name, model)

# create a TetGen mesher
mesher = sv.meshing.create_mesher(sv.meshing.Kernel.TETGEN)
model = sv.dmg.get_model(model_name)

model.compute_boundary_faces(50)

model_face_ids = [int(id) for id in model.get_face_ids()]

mesher.set_model(model)
mesher.set_walls(wall_face_ids)

#---------------------------------
# REMESH MODEL

remesh_model = sv.mesh_utils.remesh(model.get_polydata(), hmin=edge_size, hmax=edge_size)
# model.set_surface(surface=remesh_model)

# Set meshing options.
options = sv.meshing.TetGenOptions(global_edge_size=edge_size, surface_mesh_flag=True, volume_mesh_flag=True)
#options.minimum_dihedral_angle = 10.0

#----------------------------------
# MESH
 
mesher.generate_mesh(options)

mesh = mesher.get_mesh()

# adds to gui viewer
sv.dmg.add_mesh(name= model_name + "_python-mesh", mesh = mesh, model = model_name)

# print("Mesh:");
# print("  Number of nodes: {0:d}".format(mesh.GetNumberOfPoints()))
# print("  Number of elements: {0:d}".format(mesh.GetNumberOfCells()))


#--------------------------------
# WRITE FSI FILES
'''
format:
MODEL_NAME-remeshed 
    '- mesh-surfaces
        '- MODEL_NAME_mesh_face_1
        '_ MODEL_NAME_mesh_face_2
        '_ MODEL_NAME_mesh_face_3
        '_ ...
    '_ mesh-complete.mesh.vtu
'''

directory = input_path + "/mesh/" + model_name + "-remeshed"
os.makedirs(directory)
mesher.write_mesh(directory + "/mesh-complete.mesh.vtu")


# write mesh faces polygonal data to .vtp files.
print("Mesh faces ... ")
mesher.compute_model_boundary_faces(50.0)
vtp_directory = directory + "/mesh-surfaces"
os.makedirs(vtp_directory)
mesh_face_file_names = []
mesh_face_file_names_map = {}
mesh_face_pd_map = {}

print ("Face IDs: " + str(solid_face_ids))
for face_id in model_face_ids:
    mesh_face_name = vtp_directory + "/" + model_name + "_mesh_face_" + str(face_id)
    # mesher.get_face_polydata(mesh_face_name, int(face_id))
    mesh_face_pd = mesher.get_face_polydata(face_id)
    # mesh_face_pd = sv.Repository.ExportToVtk(mesh_face_name)
    print("  Face {0:d}  num nodes: {1:d}".format(int(face_id), mesh_face_pd.GetNumberOfPoints()))
    mesh_face_file_name = mesh_face_name + ".vtp"
    writer = vtk.vtkXMLPolyDataWriter()
    writer.SetFileName(mesh_face_file_name)
    writer.SetInputData(mesh_face_pd)
    writer.Update()
    writer.Write()
    mesh_face_file_names.append(mesh_face_file_name)
    mesh_face_file_names_map[int(face_id)] = mesh_face_file_name
    mesh_face_pd_map[int(face_id)] = mesh_face_pd


#--------------------------------
# EDIT SVFSI FILE MESH SECTION

f = open(svfsi_inp, "r+")
os.rename(svfsi_inp, "~" + svfsi_inp)

with open("~" + svfsi_inp, "r") as old:
    with open("svfsi.inp", "w+") as new:

        state = 1
        write_out = True

        for line in old:

            # before the mesh, keep writing
            if state == 1: 
                write_out = True
                if ("Add mesh: " + model_name) in line:
                    write_out = False
                    state = 2
            # the beginning of the remeshed mesh
            elif state == 2:
                # folder_list = [item for item in os.listdir(os.getcwd() + "/mesh") if os.path.isdir(os.path.join(os.getcwd() + "/mesh", item))]
                # folder = folder_list[0]
                remeshed = model_name + "-remeshed"
                folder = input_path + "/mesh/" + remeshed

                new.write("Add mesh: " + remeshed + " {\n")

                vtu_file = [item for item in os.listdir(folder) if item.endswith(".vtu")]

                new.write("\tMesh file path:     mesh/" + remeshed + "/" + vtu_file[0].rsplit('.',1)[0]) #FIX THE vtu_file[0] part if it's more than 0, what to put
                new.write("\n")

                vtp_files = [item for item in os.listdir(input_path + "/mesh/" + remeshed + "/mesh-surfaces") if item.endswith(".vtp")]

                for vtp in vtp_files:
                    new.write("\tAdd face: " + vtp.rsplit('.',1)[0] + " {\n")
                    new.write("\t\tFace file path: mesh/" + remeshed + "/mesh-surfaces/" + vtp + "\n")
                    new.write("\t}\n")
                new.write("}\n")

                write_out = False
                state = 3
            # still at the mesh section which needs to be replaced, don't write
            elif state == 3:
                if len(line) == 1:
                    write_out = True
                    state = 4
            # end of mesh section, continue copying the rest over
            elif state == 4:
                write_out = True

            if write_out:
                new.write(line)

            # print(str(state) + "\t"+ str(len(line)) + line)

#--------------------------------

'''
#subprocess.call(["mpiexec", "-n", "8", svfsi_path, "svFSI.inp"], cwd = inp_path)

'''