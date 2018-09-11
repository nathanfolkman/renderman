import maya.cmds as cmds
##2015 Markus Kranzler
##Python port Jacob Reuling
##Translate Maya shaders into PxrSurface

def initialize_window():
    #Check to see if the window already exists
    if cmds.window("RendermanMaterialsConverterWindow", exists=True):
        cmds.deleteUI("RendermanMaterialsConverterWindow")    
    #Create window
    UIwindow = cmds.window("RendermanMaterialsConverterWindow", title="Convert Materials", resizeToFitChildren=1, mnb=False, mxb=False, sizeable=True)
    UIDict = {}
    
    UIDict["convertForm"] = cmds.formLayout("Convert")
    UIDict["buttonsLayout"] = cmds.frameLayout(label="Maya and Renderman Materials Converter", mh=8)
    cmds.text("Use this tool to convert Maya materials or legacy Renderman materials to PxrSurface or another kind of material. Any values/connections on few basic parameters will be carried over during the conversion.", wordWrap=True)
    UIDict["oldMatsMenu"] = cmds.optionMenu(label="Old Materials")
    cmds.menuItem(label="Common Maya Materials", ann="Includes lambert, phong, phongE, and blinn.")
    cmds.menuItem(label="Old Renderman Materials", ann="Includes PxrDisney, PxrLMDiffuse, PxrLMPlastic, PxrLMMetal, PxrLMGlass, and PxrLMSubsurface.")
    cmds.menuItem(label="lambert")
    cmds.menuItem(label="phong")
    cmds.menuItem(label="phongE")
    cmds.menuItem(label="blinn")
    cmds.menuItem(label="PxrDisney")
    cmds.menuItem(label="PxrLMDiffuse")
    cmds.menuItem(label="PxrLMPlastic")
    cmds.menuItem(label="PxrLMMetal")
    cmds.menuItem(label="PxrLMGlass")
    cmds.menuItem(label="PxrLMSubsurface")
    cmds.menuItem(label="PxrSurface")
    UIDict["newMatMenu"] = cmds.optionMenu(label="New Material")
    cmds.menuItem(label="PxrSurface")
    cmds.menuItem(label="lambert")
    cmds.menuItem(label="phong")
    cmds.menuItem(label="phongE")
    cmds.menuItem(label="blinn")
    cmds.menuItem(label="PxrDisney")
    cmds.menuItem(label="PxrLMDiffuse")
    cmds.menuItem(label="PxrLMPlastic")
    cmds.menuItem(label="PxrLMMetal")
    cmds.menuItem(label="PxrLMGlass")
    cmds.menuItem(label="PxrLMSubsurface")
    UIDict["deleteOldBox"] = cmds.checkBox(label="Delete Old Material", v=True, annotation="If checked, the old material will automatically be deleted after conversion.")
    UIDict["useSelectionBox"] = cmds.checkBox(label="Convert Selected", v=False, annotation="If checked, only materials or objects that are selected will be converted regardless of material type.")
    UIDict["matchFromButton"] = cmds.button(label="Convert!", annotation="Convert materials.",
                                         command=lambda *args: mk_mayaToRenderman(cmds.optionMenu(UIDict["oldMatsMenu"], q=True, v=True), 
                                                                                  cmds.optionMenu(UIDict["newMatMenu"], q=True, v=True),
                                                                                  cmds.checkBox(UIDict["deleteOldBox"], q=True, v=True),
                                                                                  cmds.checkBox(UIDict["useSelectionBox"], q=True, v=True),
                                                                                  get_material_attributes()))
    cmds.setParent(u=True)
    cmds.formLayout(UIDict["convertForm"], edit=True, attachForm=[(UIDict["buttonsLayout"], "top", 5), (UIDict["buttonsLayout"], "left", 5)],
                                                    attachPosition=[(UIDict["buttonsLayout"], 'right', 5, 100)])    
    cmds.showWindow(UIwindow)

def mk_mayaToRenderman(matList, newMatType, deleteOld, useSelection, matAttrs):
    
    if matList == newMatType:
        cmds.error("Old Material and New Material are the same!")
    if matList == "Common Maya Materials":
        matList = ["lambert", "phong", "phongE", "blinn"]
    elif matList == "Old Renderman Materials":
        matList = ["PxrDisney", "PxrLMDiffuse", "PxrLMPlastic", "PxrLMMetal", "PxrLMGlass", "PxrLMSubsurface"]
        
    if useSelection:
        sel = cmds.ls(sl=True)
        if not sel:
            cmds.error("Please select materials or objects with materials you'd like to convert or uncheck \"Convert Selected\".")
        materials = materials_from_selection(sel)
    else:
        materials = cmds.ls(mat=True)
    
    for oldMaterial in materials:
        oldMatType = cmds.nodeType(oldMaterial)
        if oldMaterial == "particleCloud1" or (not useSelection and oldMatType not in matList):
            continue
        print "Processing Shader: "+oldMaterial+"\n"
        
        newMaterial = cmds.shadingNode(newMatType, asShader=True)
        
        #Go through common material attributes of the old material and set/connect them for the new material where applicable
        for matChannel in matAttrs:
            oldMatAttr = matAttrs[matChannel][oldMatType]
            newMatAttr = matAttrs[matChannel][newMatType]
            if newMatAttr and oldMatAttr:
                #If the attribute is connected to something, connect it to the new material
                if cmds.connectionInfo(oldMaterial+oldMatAttr, id=True):
                    matConnection = cmds.connectionInfo(oldMaterial+oldMatAttr, sfd=True)
                    #Transparency/presence is an edge case since Maya materials use color and Renderman materials use alpha
                    if "outColor" in matConnection and matChannel == "transparency":
                        matConnection = matConnection.replace("outColor", "outAlpha")
                    cmds.connectAttr(matConnection, newMaterial+newMatAttr)
                #If not, then take the attribute's value and set it to the new material's
                else:
                    #Some material attributes can share the same connections but have different data types otherwise
                    if cmds.getAttr(oldMaterial+oldMatAttr, type=True) == cmds.getAttr(newMaterial+newMatAttr, type=True):
                        #The setAttr command demands tuples to be unpacked so multi attributes such as color have to be set separately
                        if cmds.getAttr(oldMaterial+oldMatAttr, type=True) == "float3":
                            cmds.setAttr(newMaterial+newMatAttr, *cmds.getAttr(oldMaterial+oldMatAttr)[0])
                        else:
                            cmds.setAttr(newMaterial+newMatAttr, cmds.getAttr(oldMaterial+oldMatAttr))
        
        #Replace material on existing shader group
        shaderGroup = cmds.listConnections(oldMaterial+".outColor")[0]
        cmds.connectAttr(newMaterial+".outColor", shaderGroup+".surfaceShader", f=True)
        cmds.rename(newMaterial, oldMaterial.replace(oldMatType, newMatType))
        if deleteOld and oldMaterial != "lambert1":
            cmds.delete(oldMaterial)

###Goes through a list of objects and returns all of the materials or materials attached to objects in the list
def materials_from_selection(sel):
    materials = []
    matList = ["lambert", "phong", "phongE", "blinn", "PxrSurface", "PxrDisney"]
    for s in sel:
        if cmds.nodeType(s) in matList:
            materials += s
        else:
            for shape in cmds.listRelatives(s, shapes=True) or []:
                shaderGroup = cmds.listConnections(shape, type="shadingEngine")[0]
                material = cmds.listConnections(shaderGroup+".surfaceShader", d=False)
                materials += material
    return list(set(materials))
                
        
###Retrieves the names of the attributes for different types of materials
def get_material_attributes():
    #Map common material controls to their attribute names for each material
    matAttrs = {"diffuseGain":{"lambert":".diffuse", "phong":".diffuse", "phongE":".diffuse", "blinn":".diffuse", 
                               "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":None, "PxrLMMetal":None, "PxrLMGlass":None, "PxrLMSubsurface":None, 
                               "PxrSurface":".diffuseGain"},
                "diffuseColor":{"lambert":".color", "phong":".color", "phongE":".color", "blinn":".color", 
                                "PxrDisney":".baseColor", "PxrLMDiffuse":".frontColor", "PxrLMPlastic":".diffuseColor", "PxrLMMetal":None, "PxrLMGlass":None, "PxrLMSubsurface":None, 
                                "PxrSurface":".diffuseColor"},
                "diffuseRoughness":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                                    "PxrDisney":".roughness", "PxrLMDiffuse":".roughness", "PxrLMPlastic":".diffuseRoughness", "PxrLMMetal":None, "PxrLMGlass":None, "PxrLMSubsurface":None, 
                                    "PxrSurface":".diffuseRoughness"},
                "specularColor":{"lambert":None, "phong":".specularColor", "phongE":".specularColor", "blinn":".specularColor",
                                 "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":".specularColor", "PxrLMMetal":".specularColor", "PxrLMGlass":".reflectionColor", "PxrLMSubsurface":".specularColor", 
                                 "PxrSurface":".specularEdgeColor"},
                "specularRefractionIndex":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                                           "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":".specularEta", "PxrLMMetal":".eta", "PxrLMGlass":None, "PxrLMSubsurface":".specularEta", 
                                           "PxrSurface":".specularIor"},
                "specularExtinctionCoefficient":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                                                 "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":None, "PxrLMMetal":".kappa", "PxrLMGlass":None, "PxrLMSubsurface":None, 
                                                 "PxrSurface":".specularExtinctionCoeff"},
                "specularRoughness":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                                     "PxrDisney":".roughness", "PxrLMDiffuse":None, "PxrLMPlastic":".specularRoughness", "PxrLMMetal":".roughness", "PxrLMGlass":None, "PxrLMSubsurface":".specularRoughness", 
                                     "PxrSurface":".specularRoughness"},
                "specularAnisotropy":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                                      "PxrDisney":".anisotropic", "PxrLMDiffuse":None, "PxrLMPlastic":None, "PxrLMMetal":".anisotropy", "PxrLMGlass":None, "PxrLMSubsurface":".specularAnisotropy", 
                                      "PxrSurface":".specularAnisotropy"},
                "clearcoatColor":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                                  "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":".clearcoatColor", "PxrLMMetal":None, "PxrLMGlass":None, "PxrLMSubsurface":".clearcoatColor", 
                                  "PxrSurface":".clearcoatEdgeColor"},
                "clearcoatRefractionIndex":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                                            "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":".clearcoatEta", "PxrLMMetal":None, "PxrLMGlass":None, "PxrLMSubsurface":None, 
                                            "PxrSurface":".clearcoatIor"},
                "clearcoatRoughness":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                                      "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":".clearcoatRoughness", "PxrLMMetal":None, "PxrLMGlass":None, "PxrLMSubsurface":".clearcoatRoughness", 
                                      "PxrSurface":".clearcoatRoughness"},                                     
                "incandescence":{"lambert":".incandescence", "phong":".incandescence", "phongE":".incandescence", "blinn":".incandescence", 
                                 "PxrDisney":".emitColor", "PxrLMDiffuse":".incandescence", "PxrLMPlastic":".incandescence", "PxrLMMetal":None, "PxrLMGlass":None, "PxrLMSubsurface":None, 
                                 "PxrSurface":".iridescencePrimaryColor"},  
                "subsurfaceColor":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                                   "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":None, "PxrLMMetal":None, "PxrLMGlass":None, "PxrLMSubsurface":".midColor", 
                                   "PxrSurface":".subsurfaceColor"},
                "shortSubsurfaceColor":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                                        "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":None, "PxrLMMetal":None, "PxrLMGlass":None, "PxrLMSubsurface":".nearColor", 
                                        "PxrSurface":".shortSubsurfaceColor"},
                "longSubsurfaceColor":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                                       "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":None, "PxrLMMetal":None, "PxrLMGlass":None, "PxrLMSubsurface":".farColor", 
                                       "PxrSurface":".longSubsurfaceColor"},
                "subsurfaceFollowTopology":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                                            "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":None, "PxrLMMetal":None, "PxrLMGlass":None, "PxrLMSubsurface":".followTopology", 
                                            "PxrSurface":".followTopology"},
                "subsurfaceConsiderBackside":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                                              "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":None, "PxrLMMetal":None, "PxrLMGlass":None, "PxrLMSubsurface":".sssOnBothSides", 
                                              "PxrSurface":".considerBackside"},
                "glassRefractionColor":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                                       "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":None, "PxrLMMetal":None, "PxrLMGlass":".refractionColor", "PxrLMSubsurface":None, 
                                       "PxrSurface":".refractionColor"},
                "glassRouchness":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                                  "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":None, "PxrLMMetal":None, "PxrLMGlass":".roughness", "PxrLMSubsurface":None, 
                                  "PxrSurface":".glassRoughness"},
                "glassRefractiveIndex":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                                        "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":None, "PxrLMMetal":None, "PxrLMGlass":".eta", "PxrLMSubsurface":None, 
                                        "PxrSurface":".glassIor"},
                "glassThin":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                             "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":None, "PxrLMMetal":None, "PxrLMGlass":".thin", "PxrLMSubsurface":None, 
                             "PxrSurface":".thinGlass"},                                                                                                       
                "overallBump":{"lambert":".normalCamera", "phong":".normalCamera", "phongE":".normalCamera", "blinn":".normalCamera", 
                               "PxrDisney":".bumpNormal", "PxrLMDiffuse":".bumpNormal", "PxrLMPlastic":".diffuseNn", "PxrLMMetal":".bumpNormal", "PxrLMGlass":".bumpNormal", "PxrLMSubsurface":".bumpNormal", 
                               "PxrSurface":".bumpNormal"},                
                "transparency":{"lambert":".transparency", "phong":".transparency", "phongE":".transparency", "blinn":".transparency", 
                                "PxrDisney":".presence", "PxrLMDiffuse":".presence", "PxrLMPlastic":".presence", "PxrLMMetal":".presence", "PxrLMGlass":".presence", "PxrLMSubsurface":".presence", 
                                "PxrSurface":".presence"}
               }
    return matAttrs
    #The following is a template for adding more common attributes. Simply replace the "None" after a shader with the name of its attribute and it'll be matched with the attribute of any other shader in the dictionary on conversion            
                #"template":{"lambert":None, "phong":None, "phongE":None, "blinn":None, 
                #            "PxrDisney":None, "PxrLMDiffuse":None, "PxrLMPlastic":None, "PxrLMMetal":None, "PxrLMGlass":None, "PxrLMSubsurface":None, 
                #            "PxrSurface":None}
initialize_window()