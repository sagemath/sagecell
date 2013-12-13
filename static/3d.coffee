###############################################################################
# Copyright (c) 2013, William Stein
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
###############################################################################

#{defaults, required} = require('misc')

###############
## Start misc.coffee includes
###############

# convert basic structure to a JSON string
to_json = (x) ->
    JSON.stringify(x)

# Returns a new object with properties determined by those of obj1 and
# obj2.  The properties in obj1 *must* all also appear in obj2.  If an
# obj2 property has value "defaults.required", then it must appear in
# obj1.  For each property P of obj2 not specified in obj1, the
# corresponding value obj1[P] is set (all in a new copy of obj1) to
# be obj2[P].
defaults = (obj1, obj2) ->
    if not obj1?
        obj1 = {}
    error  = () ->
        try
            "(obj1=#{to_json(obj1)}, obj2=#{to_json(obj2)})"
        catch error
            ""
    if typeof(obj1) != 'object'
        # We put explicit traces before the errors in this function,
        # since otherwise they can be very hard to debug.
        console.trace()
        throw "misc.defaults -- TypeError: function takes inputs as an object #{error()}"
    r = {}
    for prop, val of obj2
        if obj1.hasOwnProperty(prop) and obj1[prop]?
            if obj2[prop] == defaults.required and not obj1[prop]?
                console.trace()
                throw "misc.defaults -- TypeError: property '#{prop}' must be specified: #{error()}"
            r[prop] = obj1[prop]
        else if obj2[prop]?  # only record not undefined properties
            if obj2[prop] == defaults.required
                console.trace()
                throw "misc.defaults -- TypeError: property '#{prop}' must be specified: #{error()}"
            else
                r[prop] = obj2[prop]
    for prop, val of obj1
        if not obj2.hasOwnProperty(prop)
            console.trace()
            throw "misc.defaults -- TypeError: got an unexpected argument '#{prop}' #{error()}"
    return r

# WARNING -- don't accidentally use this as a default:
required = defaults.required = "__!!!!!!this is a required property!!!!!!__"

############
### END misc.coffee includes
############

# WARNING: params below have different semantics than above; these are what *really* make sense....
# modified from misc.coffee, eval_until_defined
run_when_defined = (opts) ->
    opts = defaults opts,
        fn         : required
        start_delay  : 100    # initial delay beforing calling f again.  times are all in milliseconds
        max_time     : 10000  # error if total time spent trying will exceed this time
        exp_factor   : 1.4
        cb           : required # cb(err, eval(code))
        err          : required #
    delay = undefined
    total = 0
    f = () ->
        result = opts.fn()
        if result?
            opts.cb(result)
        else
            if not delay?
                delay = opts.start_delay
            else
                delay *= opts.exp_factor
            total += delay
            if total > opts.max_time
                opts.err("failed to eval code within #{opts.max_time}")
            else
                setTimeout(f, delay)
    f()



component_to_hex = (c) ->
    hex = c.toString(16);
    if hex.length == 1
        return "0" + hex
    else
        return hex

rgb_to_hex = (r, g, b) -> "#" + component_to_hex(r) + component_to_hex(g) + component_to_hex(b)

class SalvusThreeJS
    constructor: (opts) ->
        @opts = defaults opts,
            element         : required
            width           : undefined
            height          : undefined
            renderer        : undefined  # 'webgl', 'canvas2d', or undefined = "webgl if available; otherwise, canvas2d"
            trackball       : true
            light           : true
            background      : undefined
            foreground      : undefined
            camera_distance : 10
        @scene = new THREE.Scene()
        @opts.width  = if opts.width? then opts.width else $(window).width()*.9
        @opts.height = if opts.height? then opts.height else $(window).height()*.6
        if not @opts.renderer?
            if Detector.webgl
                @opts.renderer = 'webgl'
            else
                @opts.renderer = 'canvas2d'

        if @opts.renderer == 'webgl'
            @opts.element.find(".salvus-3d-viewer-renderer").text("webgl")
            @renderer = new THREE.WebGLRenderer
                antialias             : true
                preserveDrawingBuffer : true
        else
            @opts.element.find(".salvus-3d-viewer-renderer").text("canvas2d")
            @renderer = new THREE.CanvasRenderer(antialias:true)
        @renderer.setSize(@opts.width, @opts.height)
        @renderer.setClearColor(0xffffff, 1);
        if not @opts.background?
            @opts.background = "rgba(1,1,1,0);" # TODO: make this transparent -- looks better with themes
            if not @opts.foreground?
                @opts.foreground = "#000000" # black

        # Placing renderer in the DOM.
        @opts.element.find(".salvus-3d-canvas").css('background':@opts.background).append($(@renderer.domElement))

        if not @opts.foreground?
            c = @opts.element.find(".salvus-3d-canvas").css('background')
            i = c.indexOf(')')
            z = (255-parseInt(a) for a in c.slice(4,i).split(','))
            @opts.foreground = rgb_to_hex(z[0], z[1], z[2])

        @_center = @scene.position
        @add_camera(distance:@opts.camera_distance)
        if @opts.trackball
            @set_trackball_controls()

        @lights = {static: [], rotating: [], camera_distance: @camera.position.distanceTo(@_center)}
        @controls.addEventListener('change', @controlChange)

        @_animate = false
        @_animation_frame = false

        ###
        # This is purely for debugging
        window.MYSCENE=this
        @three = THREE
        ###

    data_url: (type='png') =>   # 'png' or 'jpeg'
        return @renderer.domElement.toDataURL("image/#{type}")

    set_trackball_controls: () =>
        ###
        # other options: rotate object instead of camera
        # see: https://github.com/mrdoob/three.js/issues/1220#issuecomment-3753576
        # see: https://github.com/mrdoob/three.js/issues/781
        ###
        if @controls?
            return
        @controls = new THREE.TrackballControls(@camera, @renderer.domElement)
        @controls.dynamicDampingFactor = 0.3
        @controls.noRoll=true
        if @_center?
            @controls.target = @_center
        @controls.addEventListener('change', @controlChange)
        @controls.addEventListener('start', (() => @_animate=true; @_animation_frame=requestAnimationFrame(@animate)))
        @controls.addEventListener('end', (() => @_animate=false))

    add_camera: (opts) =>
        opts = defaults opts,
            distance : 10

        view_angle = 45
        aspect     = @opts.width/@opts.height
        near       = 0.1
        far        = Math.max(20000, opts.distance*2)

        @camera    = new THREE.PerspectiveCamera(view_angle, aspect, near, far)
        @scene.add(@camera)
        @camera.position.set(opts.distance, opts.distance, opts.distance)
        @camera.lookAt(@scene.position)
        @camera.up = new THREE.Vector3(0,0,1)
        @camera.updateMatrix()

    add_lights: (obj) =>
        handlers =
            ambient: @make_ambient_light
            directional: @make_directional_light
            point: @make_point_light
            spot: @make_spot_light
        @lights.camera_distance = @camera.position.distanceTo(@_center)
        for l in obj.lights
            type = l.light_type
            delete l.light_type
            fixed = l.fixed
            delete l.fixed
            delete l.type # should always be 'light'
            light = handlers[type](l)
            if fixed=="camera"
                # convert the light coordinates (which are world coordinates)
                # to camera coordinates before adding the light to the camera
                #light.up = @camera.up
                m = new THREE.Matrix4()
                light.position.applyMatrix4(m.getInverse(@camera.matrix))
                @lights.rotating.push(light)
                @camera.add(light)
            else
                @lights.static.push(light)
                @scene.add(light)
        @render_scene()

    make_ambient_light: (opts) =>
        o = defaults opts,
            color: 0x444444
        return new THREE.AmbientLight(o.color)
    make_directional_light: (opts) =>
        o = defaults opts,
            position: required
            intensity: 1.0
            color: 0xffffff
        light = new THREE.DirectionalLight(o.color, o.intensity)
        light.position.set(o.position[0], o.position[1], o.position[2])
        return light
    make_point_light: (opts) =>
        o = defaults opts,
            position: required
            intensity: 1.0
            color: 0xffffff
            distance: undefined
        light = new THREE.PointLight(o.color, o.intensity, o.distance)
        light.position.set(o.position[0], o.position[1], o.position[2])
        return light
    make_spot_light: (opts) =>
        o = defaults opts,
            position: required
            intensity: 1.0
            color: 0xffffff
            distance: undefined
            angle: undefined
            exponent: undefined
        light = new THREE.SpotLight(o.color, o.intensity, o.distance, o.angle, o.exponent)
        light.position.set(o.position[0], o.position[1], o.position[2])
        return light

    make_lambert_material: (opts) =>
        o = defaults opts,
            opacity: 1
            #ambient: 0x444444
            ambient: 0xffffff
            diffuse: 0x222222
            specular: 0xffffff
            color: required
            emmissive: 0x222222
            shininess: 100
            overdraw: true
            polygonOffset: true
            polygonOffsetFactor: 1
            polygonOffsetUnits: 1
            side: THREE.DoubleSide
        o.transparent = o.opacity < 1
        return new THREE.MeshLambertMaterial(o)

    make_phong_material: (opts) =>
        o = defaults opts,
            opacity: 1
            ambient: 0x222222
            #ambient: 0xffffff
            diffuse: 0x222222
            specular: 0xffffff
            color: required
            emmissive: 0x222222
            shininess: 100
            overdraw: true
            polygonOffset: true
            polygonOffsetFactor: 1
            polygonOffsetUnits: 1
            side: THREE.DoubleSide
        o.transparent = o.opacity < 1
        return new THREE.MeshPhongMaterial(o)

    make_wireframe_material: () =>
        o = defaults {},
            color: 0x222222
            transparent: true
            opacity: .2
        o.wireframe = true
        return new THREE.MeshBasicMaterial(o)

    make_text: (opts, material) =>
        o = defaults opts,
            pos              : [0,0,0]
            string           : required
            fontsize         : 14
            fontface         : 'Arial'
            color            : "#000000"   # anything that is valid to canvas context, e.g., "rgba(249,95,95,0.7)" is also valid.
            border_thickness : 0
            constant_size    : true  # if true, then text is automatically resized when the camera moves;
            # WARNING: if constant_size, don't remove text from scene (or if you do, note that it is slightly inefficient still.)
        canvas  = document.createElement("canvas")
        context = canvas.getContext("2d")

        textHeight = o.fontsize*4 # one pt = 4 pixels
        canvas.height = textHeight
        font = "Normal " + textHeight + "px " + o.fontface

        context.font = font
        metrics = context.measureText(o.string);
        textWidth = metrics.width
        canvas.width = textWidth

        context.textAlign = "center"
        context.textBaseline = "middle"
        context.fillStyle = o.color
        context.font = font
        context.fillText(o.string, textWidth/2, textHeight/2)
        texture = new THREE.Texture(canvas)
        texture.needsUpdate = true
        spriteMaterial = new THREE.SpriteMaterial
            map                  : texture
            transparent          : true

        sprite = new THREE.Sprite(spriteMaterial)
        p = o.pos
        sprite.position.set(p[0], p[1], p[2])
        # TODO: this scaling needs to be determined somehow---right now it depends on the world coordinates in the picture
        actualFontSize=0.2
        sprite.scale.set(textWidth / textHeight * actualFontSize, actualFontSize, 1)
        
        if o.constant_size
            if not @_text?
                @_text = [sprite]
            else
                @_text.push(sprite)
        
        return sprite

    make_line : (opts, material) =>
        o = defaults opts,
            points     : required
            thickness  : 1
            arrowhead : false  # TODO
        m = material || {}
        m.color = m.color || 0
        geometry = new THREE.Geometry()
        for a in o.points
            geometry.vertices.push(new THREE.Vector3(a[0],a[1],a[2]))
        return new THREE.Line(geometry, new THREE.LineBasicMaterial({linewidth: o.thickness, color: m.color}))

    make_point: (opts, material) =>
        o = defaults opts,
            position: [0,0,0]
            size: 1
        geometry = new THREE.SphereGeometry(Math.sqrt(o.size)/50,8,8)
        m = @make_lambert_material(material)
        mesh = new THREE.Mesh(geometry, m)
        mesh.position.set(o.position[0], o.position[1], o.position[2])
        return mesh

    make_sphere: (opts, material) =>
        # centered at the origin
        o = defaults opts,
            radius: 1
            position: [0,0,0]
        geometry = new THREE.SphereGeometry(o.radius, 40,24)
        m1 = @make_lambert_material(material)
        m2 = @make_wireframe_material()
        return THREE.SceneUtils.createMultiMaterialObject(geometry, [m1, m2])

    make_box: (opts, material) =>
        # centered at the origin
        o = defaults opts,
            size: required

        geometry = new THREE.CubeGeometry(o.size[0], o.size[1], o.size[2])
        m1 = @make_lambert_material(material)
        m2 = @make_wireframe_material()
        return THREE.SceneUtils.createMultiMaterialObject(geometry, [m1, m2])

    make_cylinder: (opts, material) =>
        o = defaults opts,
            radius:    1
            height:       1
            closed: true

        geometry = new THREE.CylinderGeometry(o.radius, o.radius, o.height, 20, 1, !o.closed)
        m1 = @make_lambert_material(material)
        m2 = @make_wireframe_material()
        s = THREE.SceneUtils.createMultiMaterialObject(geometry, [m1, m2])
        # Sage assumes base is on the xy plane pointing up the z-axis
        s.rotateX(Math.PI/2).translateY(o.height/2)
        return s
        
    make_cone: (opts, material) =>
        o = defaults opts,
            bottomradius:    1
            height:    1
            closed: true

        geometry = new THREE.CylinderGeometry(0, o.bottomradius, o.height, 20, 1, !o.closed)
        m1 = @make_lambert_material(material)
        m2 = @make_wireframe_material()
        s = THREE.SceneUtils.createMultiMaterialObject(geometry, [m1, m2])
        # Sage assumes base is on the xy plane pointing up the z-axis
        s.rotateX(Math.PI/2).translateY(o.height/2)
        return s

    make_group: (opts) =>
        o = defaults opts,
            matrix : [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
            children : required
        obj = new THREE.Object3D()
        m = o.matrix
        obj.matrixAutoUpdate = false # tell three.js to not update the matrix based on position, rotation, etc.
        obj.matrix.set(m[0], m[1], m[2], m[3],
                            m[4], m[5], m[6], m[7],
                            m[8], m[9], m[10], m[11],
                            m[12], m[13], m[14], m[15])
        obj.add(@make_object(i)) for i in o.children
        return obj

    make_index_face_set: (opts, material)=>
        o = defaults opts,
            vertices: []
            face3: []
            face4: []
            face5: []

        geometry = new THREE.Geometry()
        for v in opts.vertices
            geometry.vertices.push(new THREE.Vector3(v[0], v[1], v[2]))
        for f in opts.face3
            geometry.faces.push(new THREE.Face3(f[0], f[1], f[2]))
        for f in opts.face4
            geometry.faces.push(new THREE.Face3(f[0], f[1], f[2]))
            geometry.faces.push(new THREE.Face3(f[0], f[2], f[3]))
        for f in opts.face5
            geometry.faces.push(new THREE.Face3(f[0], f[1], f[2]))
            geometry.faces.push(new THREE.Face3(f[0], f[2], f[3]))
            geometry.faces.push(new THREE.Face3(f[0], f[3], f[4]))

        geometry.mergeVertices()
        geometry.computeCentroids()
        geometry.computeFaceNormals()
        geometry.computeVertexNormals()
        geometry.computeBoundingSphere()

        m1 = @make_lambert_material(material)
        m2 = @make_wireframe_material()
        return THREE.SceneUtils.createMultiMaterialObject(geometry, [m1, m2])

    make_object: (obj) =>
        handlers =
          text: @make_text
          index_face_set: @make_index_face_set
          line: @make_line
          point: @make_point
          sphere: @make_sphere
          cone: @make_cone
          cylinder: @make_cylinder
          box: @make_box
        type = obj.type
        delete obj.type
        o = false
        if type == 'group'
            o = @make_group(obj)
        else if type == 'object'
            geometry_type = obj.geometry.type
            delete obj.geometry.type
            o = handlers[geometry_type](obj.geometry, obj.texture)
        return o

    add_3dgraphics_obj: (opts) =>
        opts = defaults opts,
            obj       : required
            wireframe : false

        @scene.add(@make_object(opts.obj))
        @render_scene(true)

    # always call this after adding things to the scene to make sure track
    # controls are sorted out, etc.   Set draw:false, if you don't want to
    # actually *see* a frame.
    set_frame: (opts) =>
        o = defaults opts,
            xmin : required
            xmax : required
            ymin : required
            ymax : required
            zmin : required
            zmax : required
            color     : @opts.foreground
            thickness : .4
            labels    : true  # whether to draw three numerical labels along each of the x, y, and z axes.
            fontsize  : 14
            draw   : true

        @_frame_params = o

        eps = 0.1
        if Math.abs(o.xmax-o.xmin)<eps
            o.xmax += 1
            o.xmin -= 1
        if Math.abs(o.ymax-o.ymin)<eps
            o.ymax += 1
            o.ymin -= 1
        if Math.abs(o.zmax-o.zmin)<eps
            o.zmax += 1
            o.zmin -= 1

        if @frame?
            # remove existing frame
            @scene.remove(@frame)
            @frame = undefined

        if o.draw
            geometry = new THREE.Geometry()
            vertices = [ new THREE.Vector3(o.xmin, o.ymin, o.zmin),
                         new THREE.Vector3(o.xmax, o.ymin, o.zmin),
                         new THREE.Vector3(o.xmax, o.ymax, o.zmin),
                         new THREE.Vector3(o.xmin, o.ymax, o.zmin),
                         new THREE.Vector3(o.xmin, o.ymin, o.zmax),
                         new THREE.Vector3(o.xmax, o.ymin, o.zmax),
                         new THREE.Vector3(o.xmax, o.ymax, o.zmax),
                         new THREE.Vector3(o.xmin, o.ymax, o.zmax)]
            geometry.vertices.push(vertices[0], vertices[1],
                                   vertices[1], vertices[2],
                                   vertices[2], vertices[3],
                                   vertices[3], vertices[0],
                                   vertices[4], vertices[5],
                                   vertices[5], vertices[6],
                                   vertices[6], vertices[7],
                                   vertices[7], vertices[4],
                                   vertices[0], vertices[4],
                                   vertices[1], vertices[5],
                                   vertices[2], vertices[6],
                                   vertices[3], vertices[7]
                                   )
            material = new THREE.LineBasicMaterial
                color              : o.color
                #linewidth : o.thickness
            @frame = new THREE.Line(geometry, material, THREE.LinePieces)
            @scene.add(@frame)

        if o.labels
            if @_frame_labels?
                for x in @_frame_labels
                    @scene.remove(x)

            @_frame_labels = []

            l = (a,b) ->
                if not b?
                    z = a
                else
                    z = (a+b)/2
                z = z.toFixed(2)
                return (z*1).toString()

            txt = (x,y,z,text) =>
                t = @make_text(pos:[x,y,z], string:text, fontsize:o.fontsize, color:o.color, constant_size:false, {})
                @_frame_labels.push(t)
                @scene.add(t)

            offset = 0.075
            mx = (o.xmin+o.xmax)/2
            my = (o.ymin+o.ymax)/2
            mz = (o.zmin+o.zmax)/2
            @_center = new THREE.Vector3(mx,my,mz)
            @controls.target = @_center

            if o.draw
                e = (o.ymax - o.ymin)*offset
                txt(o.xmax,o.ymin-e,o.zmin, l(o.zmin))
                txt(o.xmax,o.ymin-e,mz, "z=#{l(o.zmin,o.zmax)}")
                txt(o.xmax,o.ymin-e,o.zmax,l(o.zmax))

                e = (o.xmax - o.xmin)*offset
                txt(o.xmax+e,o.ymin,o.zmin,l(o.ymin))
                txt(o.xmax+e,my,o.zmin, "y=#{l(o.ymin,o.ymax)}")
                txt(o.xmax+e,o.ymax,o.zmin,l(o.ymax))

                e = (o.ymax - o.ymin)*offset
                txt(o.xmax,o.ymax+e,o.zmin,l(o.xmax))
                txt(mx,o.ymax+e,o.zmin, "x=#{l(o.xmin,o.xmax)}")
                txt(o.xmin,o.ymax+e,o.zmin,l(o.xmin))

        v = new THREE.Vector3(mx, my, mz)
        @camera.lookAt(v)
        @render_scene()
        @controls?.handleResize()
        if o.draw
            @render_scene()

    animate: () =>
        if @_animate
            @_animation_frame = requestAnimationFrame(@animate)
        else
            @_animation_frame = false
        @controls?.update()

    update_rotating_lights: () =>
        camera_distance = @camera.position.distanceTo(@_center)
        # we may want relative error here in case we have an extremely small plot
        if Math.abs(camera_distance - @lights.camera_distance)>1e-6
            camera_ratio = camera_distance/@lights.camera_distance
            for l in @lights.rotating
                l.position.setLength(l.position.distanceTo(@_center)*camera_ratio)
            @lights.camera_distance = camera_distance

    controlChange: () =>
        # if there was any actual control updates, animate at least one more frame
        if !@_animation_frame
            @_animation_frame = requestAnimationFrame(@animate)
        @update_rotating_lights()
        @render_scene()

    render_scene: () =>
        # rescale all text in scene
        #if (new_pos or force) and @_center?
        #    s = @camera.position.distanceTo(@_center) / 3
        #    if @_text?
        #        for sprite in @_text
        #            sprite.scale.set(s,s,s)
        #    if @_frame_labels?
        #        for sprite in @_frame_labels
        #            sprite.scale.set(s,s,s)
        @renderer.render(@scene, @camera)

$.fn.salvus_threejs = (opts={}) ->
    @each () ->
        elt = $(this)
        e = $(".salvus-3d-templates .salvus-3d-viewer").clone()
        elt.empty().append(e)
        opts.element = e
        elt.data('salvus-threejs', new SalvusThreeJS(opts))

root = exports ? this
root.run_when_defined = run_when_defined

