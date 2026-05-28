/**
 * Klyro 3D — Neural network particle hero
 * Three.js r128 (global THREE from CDN)
 */
(function () {
  'use strict';

  window.KlyroThree = {
    init: function (canvasId) {
      var canvas = document.getElementById(canvasId);
      if (!canvas || typeof THREE === 'undefined') return;

      var W = canvas.offsetWidth || window.innerWidth;
      var H = canvas.offsetHeight || 600;

      var renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
      renderer.setSize(W, H);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

      var scene = new THREE.Scene();
      var camera = new THREE.PerspectiveCamera(60, W / H, 0.1, 1000);
      camera.position.z = 80;

      var N_PARTICLES = 160;
      var positions = new Float32Array(N_PARTICLES * 3);
      var colors = new Float32Array(N_PARTICLES * 3);
      var spread = 90;

      var palette = [
        new THREE.Color('#06b6d4'),
        new THREE.Color('#8b5cf6'),
        new THREE.Color('#3b82f6'),
        new THREE.Color('#22d3ee'),
        new THREE.Color('#a78bfa'),
      ];

      for (var i = 0; i < N_PARTICLES; i++) {
        var theta = Math.random() * Math.PI * 2;
        var phi = Math.acos(2 * Math.random() - 1);
        var r = 20 + Math.random() * spread;
        positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
        positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
        positions[i * 3 + 2] = r * Math.cos(phi) * 0.4;

        var c = palette[Math.floor(Math.random() * palette.length)];
        colors[i * 3] = c.r;
        colors[i * 3 + 1] = c.g;
        colors[i * 3 + 2] = c.b;
      }

      var geoPts = new THREE.BufferGeometry();
      geoPts.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      geoPts.setAttribute('color', new THREE.BufferAttribute(colors, 3));

      var matPts = new THREE.PointsMaterial({
        size: 1.4,
        vertexColors: true,
        transparent: true,
        opacity: 0.75,
        sizeAttenuation: true,
      });

      var points = new THREE.Points(geoPts, matPts);
      scene.add(points);

      var linesMesh = null;
      (function buildLines() {
        var linePositions = [];
        var THRESHOLD = 30;
        for (var a = 0; a < N_PARTICLES; a++) {
          for (var b = a + 1; b < N_PARTICLES; b++) {
            var dx = positions[a * 3] - positions[b * 3];
            var dy = positions[a * 3 + 1] - positions[b * 3 + 1];
            var dz = positions[a * 3 + 2] - positions[b * 3 + 2];
            var dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
            if (dist < THRESHOLD) {
              linePositions.push(
                positions[a * 3], positions[a * 3 + 1], positions[a * 3 + 2],
                positions[b * 3], positions[b * 3 + 1], positions[b * 3 + 2]
              );
            }
          }
        }
        var geoL = new THREE.BufferGeometry();
        geoL.setAttribute('position', new THREE.BufferAttribute(new Float32Array(linePositions), 3));
        var matL = new THREE.LineBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.10 });
        linesMesh = new THREE.LineSegments(geoL, matL);
        scene.add(linesMesh);
      })();

      var orbGeo = new THREE.SphereGeometry(10, 64, 64);
      var orbMat = new THREE.MeshStandardMaterial({
        color: 0x06b6d4,
        emissive: 0x0891b2,
        emissiveIntensity: 0.8,
        transparent: true,
        opacity: 0.55,
        roughness: 0.1,
        metalness: 0.9,
        wireframe: false,
      });
      var orbMesh = new THREE.Mesh(orbGeo, orbMat);
      scene.add(orbMesh);

      var wireGeo = new THREE.SphereGeometry(10.1, 16, 16);
      var wireMat = new THREE.MeshBasicMaterial({ color: 0x22d3ee, wireframe: true, transparent: true, opacity: 0.12 });
      scene.add(new THREE.Mesh(wireGeo, wireMat));

      scene.add(new THREE.AmbientLight(0x0a0a1a, 1));
      var ptLight1 = new THREE.PointLight(0x06b6d4, 3, 120);
      ptLight1.position.set(30, 30, 40);
      scene.add(ptLight1);

      var mouse = { x: 0, y: 0, tx: 0, ty: 0 };
      document.addEventListener('mousemove', function (e) {
        mouse.tx = (e.clientX / window.innerWidth - 0.5) * 2;
        mouse.ty = (e.clientY / window.innerHeight - 0.5) * 2;
      }, { passive: true });

      window.addEventListener('resize', function () {
        W = canvas.offsetWidth || window.innerWidth;
        H = canvas.offsetHeight || 600;
        camera.aspect = W / H;
        camera.updateProjectionMatrix();
        renderer.setSize(W, H);
      });

      var t = 0;
      function animate() {
        requestAnimationFrame(animate);
        t += 0.005;

        mouse.x += (mouse.tx - mouse.x) * 0.05;
        mouse.y += (mouse.ty - mouse.y) * 0.05;

        points.rotation.y = t * 0.12 + mouse.x * 0.15;
        points.rotation.x = mouse.y * 0.10;
        if (linesMesh) {
          linesMesh.rotation.y = points.rotation.y;
          linesMesh.rotation.x = points.rotation.x;
        }

        orbMesh.rotation.y = t * 0.3;
        orbMesh.rotation.z = t * 0.15;
        var breathe = 1 + 0.04 * Math.sin(t * 1.5);
        orbMesh.scale.setScalar(breathe);
        orbMat.emissiveIntensity = 0.7 + 0.3 * Math.sin(t * 2);
        ptLight1.intensity = 3 + 1.5 * Math.sin(t * 1.8);

        renderer.render(scene, camera);
      }
      animate();
    },
  };
})();
