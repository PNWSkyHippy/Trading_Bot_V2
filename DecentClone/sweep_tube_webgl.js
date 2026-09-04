        function segmentIsSweepableTube(seg) {
            return !!seg && !segmentIsRectRoom(seg) && !segmentIsChamber(seg) && !segmentIsRoundJunction(seg);
        }

        function sweepTextureKey(seg) {
            return String(seg?.wallTextureId || defaultWallTextureId || DEFAULT_WALL_TEXTURE_ID);
        }

        function sweepSegmentZRange(seg) {
            const length = Math.max(1, Number(seg.length) || builder.length);
            const fromTrim = roundJunctionEndpointRenderTrim(seg, 'from');
            const toTrim = roundJunctionEndpointRenderTrim(seg, 'to');
            const z0 = fromTrim !== null ? fromTrim : 0;
            const z1 = toTrim !== null ? length - toTrim : length;
            return { length, z0, z1: Math.max(z0 + 1, z1) };
        }

        function sweepTravelDir(seg, direction) {
            const forward = normalize(seg.forward || builder.forward);
            return direction < 0 ? scaleVec(forward, -1) : forward;
        }

        function sweepPointAtZ(seg, z) {
            return addVec(seg.from, scaleVec(normalize(seg.forward || builder.forward), z));
        }

        function sweepTravelZ(seg, direction, which, inset) {
            const { z0, z1 } = sweepSegmentZRange(seg);
            const pad = Math.max(0, inset || 0);
            if (direction > 0) return which === 'start' ? z0 + pad : z1 - pad;
            return which === 'start' ? z1 - pad : z0 + pad;
        }

        function sweepUsableLength(seg) {
            const { z0, z1 } = sweepSegmentZRange(seg);
            return Math.max(1, z1 - z0);
        }

        function sweepOrthonormalFrame(tangent, rightHint) {
            const t = normalize(tangent);
            let r = subVec(rightHint, scaleVec(t, dot(rightHint, t)));
            let mag = Math.hypot(r.x, r.y, r.z);
            if (mag < 0.000001) {
                r = Math.abs(t.y) < 0.9 ? { x: 1, y: 0, z: 0 } : { x: 0, y: 0, z: 1 };
                r = subVec(r, scaleVec(t, dot(r, t)));
                mag = Math.hypot(r.x, r.y, r.z);
            }
            r = scaleVec(r, 1 / Math.max(0.000001, mag));
            return { tangent: t, right: r, down: normalize(cross(t, r)) };
        }

        function planSweepFillet(entryA, entryB) {
            const t1 = sweepTravelDir(entryA.seg, entryA.direction);
            const t2 = sweepTravelDir(entryB.seg, entryB.direction);
            const exitA = sweepPointAtZ(entryA.seg, sweepTravelZ(entryA.seg, entryA.direction, 'end', 0));
            const enterB = sweepPointAtZ(entryB.seg, sweepTravelZ(entryB.seg, entryB.direction, 'start', 0));
            const joint = lerpVec(exitA, enterB, 0.5);
            const cos = Math.max(-1, Math.min(1, dot(t1, t2)));
            const alpha = Math.acos(cos);
            const tubeRadius = Math.min(
                Number(entryA.seg.radius) || builder.radius,
                Number(entryB.seg.radius) || builder.radius
            );
            const straight = {
                kind: 'join',
                alpha,
                insetA: 0,
                insetB: 0,
                joint,
                t1,
                t2,
                tubeRadius
            };
            if (alpha < TUNNEL_SWEEP_MIN_TURN_RAD || alpha > TUNNEL_SWEEP_MAX_TURN_RAD) return straight;
            const tanHalf = Math.tan(alpha * 0.5);
            if (tanHalf < 0.0001) return straight;
            const maxInset = Math.min(
                sweepUsableLength(entryA.seg) * 0.42,
                sweepUsableLength(entryB.seg) * 0.42,
                Math.max(48, tubeRadius * 1.65)
            );
            const inset = Math.min(maxInset, tubeRadius * tanHalf);
            if (inset < 8) return straight;
            const radius = inset / tanHalf;
            const binormal = cross(t1, t2);
            const binMag = Math.hypot(binormal.x, binormal.y, binormal.z);
            if (binMag < 0.000001) return straight;
            const B = scaleVec(binormal, 1 / binMag);
            const tangentA = sweepPointAtZ(
                entryA.seg,
                sweepTravelZ(entryA.seg, entryA.direction, 'end', inset)
            );
            const tangentB = sweepPointAtZ(
                entryB.seg,
                sweepTravelZ(entryB.seg, entryB.direction, 'start', inset)
            );
            const toward = cross(B, t1);
            const towardMag = Math.hypot(toward.x, toward.y, toward.z) || 1;
            return {
                kind: 'arc',
                alpha,
                insetA: inset,
                insetB: inset,
                radius,
                center: addVec(tangentA, scaleVec(toward, radius / towardMag)),
                binormal: B,
                tangentA,
                tangentB,
                t1,
                t2,
                joint,
                tubeRadius
            };
        }

        function pushSweepSample(samples, center, tangent, rightHint, radius, segIndex) {
            const prev = samples[samples.length - 1];
            if (prev && distanceSq(prev.center, center) < 1) return;
            const hint = prev
                ? transportTextureRunReference(prev.right, prev.tangent, tangent)
                : rightHint;
            const frame = sweepOrthonormalFrame(tangent, hint);
            const arc = prev ? prev.arc + Math.sqrt(distanceSq(prev.center, center)) : 0;
            samples.push({
                center: copyVec(center),
                tangent: frame.tangent,
                right: frame.right,
                down: frame.down,
                radius,
                arc,
                segIndex
            });
        }

        function emitSweepStraight(samples, entry, zStart, zEnd, rightHint) {
            const seg = entry.seg;
            const span = zEnd - zStart;
            if (Math.abs(span) < 1) {
                pushSweepSample(
                    samples,
                    sweepPointAtZ(seg, zStart),
                    sweepTravelDir(seg, entry.direction),
                    rightHint,
                    Number(seg.radius) || builder.radius,
                    entry.index
                );
                return;
            }
            const travel = sweepTravelDir(seg, entry.direction);
            const radius = Number(seg.radius) || builder.radius;
            const step = Math.max(28, radius * 0.35);
            const count = Math.max(1, Math.ceil(Math.abs(span) / step));
            for (let i = 0; i <= count; i++) {
                const z = zStart + span * (i / count);
                pushSweepSample(samples, sweepPointAtZ(seg, z), travel, rightHint, radius, entry.index);
            }
        }

        function emitSweepFillet(samples, fillet, entryA, entryB, rightHint) {
            const enterB = sweepPointAtZ(
                entryB.seg,
                sweepTravelZ(entryB.seg, entryB.direction, 'start', fillet?.insetB || 0)
            );
            const t2 = sweepTravelDir(entryB.seg, entryB.direction);
            const radiusB = Number(entryB.seg.radius) || builder.radius;
            if (!fillet || fillet.kind !== 'arc') {
                pushSweepSample(samples, enterB, t2, rightHint, radiusB, entryB.index);
                return;
            }
            const startVec = subVec(fillet.tangentA, fillet.center);
            const steps = Math.max(3, Math.ceil(fillet.alpha / TUNNEL_SWEEP_ARC_STEP_RAD));
            for (let i = 1; i <= steps; i++) {
                const t = i / steps;
                const point = addVec(
                    fillet.center,
                    rotateVector(startVec, fillet.binormal, fillet.alpha * t)
                );
                const tangent = rotateVector(fillet.t1, fillet.binormal, fillet.alpha * t);
                pushSweepSample(samples, point, tangent, rightHint, fillet.tubeRadius, entryA.index);
            }
            if (distanceSq(samples[samples.length - 1].center, enterB) > 4) {
                pushSweepSample(samples, enterB, t2, rightHint, radiusB, entryB.index);
            }
        }

        function buildSweepPathSamples(entries) {
            const samples = [];
            if (!entries.length) return samples;
            const fillets = [];
            for (let i = 0; i < entries.length - 1; i++) {
                fillets.push(planSweepFillet(entries[i], entries[i + 1]));
            }
            const rightHint = normalize(entries[0].seg.right || builder.right);
            for (let i = 0; i < entries.length; i++) {
                const entry = entries[i];
                const insetStart = i > 0 ? (fillets[i - 1].insetB || 0) : 0;
                const insetEnd = i < fillets.length ? (fillets[i].insetA || 0) : 0;
                emitSweepStraight(
                    samples,
                    entry,
                    sweepTravelZ(entry.seg, entry.direction, 'start', insetStart),
                    sweepTravelZ(entry.seg, entry.direction, 'end', insetEnd),
                    rightHint
                );
                if (i < fillets.length) {
                    emitSweepFillet(samples, fillets[i], entry, entries[i + 1], rightHint);
                }
            }
            const total = samples.length ? samples[samples.length - 1].arc : 1;
            const denom = Math.max(0.0001, total);
            for (const sample of samples) sample.v = sample.arc / denom;
            return samples;
        }

        function buildSweepTubeGpuMesh(samples, radialSegments, uvMode) {
            radialSegments = Math.max(12, Math.min(48, Math.round(radialSegments || TUNNEL_WEBGL_RADIAL_SEGMENTS)));
            if (!samples || samples.length < 2) return null;
            const row = radialSegments + 1;
            if (samples.length * row > 65000) {
                const keep = Math.max(2, Math.floor(65000 / row));
                samples = samples.filter((_, i) => i === 0 || i === samples.length - 1 || i % Math.ceil(samples.length / keep) === 0);
                if (samples.length > keep) samples = samples.slice(0, keep);
            }
            const keyBits = samples.map(s =>
                `${s.center.x.toFixed(1)},${s.center.y.toFixed(1)},${s.center.z.toFixed(1)},${s.radius.toFixed(1)},${s.v.toFixed(4)}`
            );
            const key = `${TUNNEL_WEBGL_MESH_CACHE_VERSION}|sweepRibbon|${uvMode}|${radialSegments}|${keyBits.join('|')}`;
            if (tunnelWebGL.meshCache.has(key)) return tunnelWebGL.meshCache.get(key);

            const vertices = [];
            const texCoords = [];
            const indices = [];
            const tileV = uvMode === 'tile';
            for (const sample of samples) {
                for (let i = 0; i <= radialSegments; i++) {
                    const u = i / radialSegments;
                    const theta = u * Math.PI * 2;
                    const c = Math.cos(theta);
                    const s = Math.sin(theta);
                    vertices.push(
                        sample.center.x + sample.right.x * c * sample.radius + sample.down.x * s * sample.radius,
                        sample.center.y + sample.right.y * c * sample.radius + sample.down.y * s * sample.radius,
                        sample.center.z + sample.right.z * c * sample.radius + sample.down.z * s * sample.radius
                    );
                    texCoords.push(u, tileV ? sample.arc / TUNNEL_TEXTURE_TILE_WORLD : sample.v);
                }
            }
            for (let j = 0; j < samples.length - 1; j++) {
                for (let i = 0; i < radialSegments; i++) {
                    const first = j * row + i;
                    const second = first + row;
                    indices.push(first, first + 1, second, second, first + 1, second + 1);
                }
            }
            const gl = tunnelWebGL.gl;
            const mesh = {
                indexCount: indices.length,
                vertexBuffer: gl.createBuffer(),
                texCoordBuffer: gl.createBuffer(),
                indexBuffer: gl.createBuffer()
            };
            gl.bindBuffer(gl.ARRAY_BUFFER, mesh.vertexBuffer);
            gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(vertices), gl.STATIC_DRAW);
            gl.bindBuffer(gl.ARRAY_BUFFER, mesh.texCoordBuffer);
            gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(texCoords), gl.STATIC_DRAW);
            gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, mesh.indexBuffer);
            gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(indices), gl.STATIC_DRAW);
            tunnelWebGL.meshCache.set(key, mesh);
            trimCylinderMeshCache();
            return mesh;
        }

        function sweepEndpointNeighbors(index, endKind) {
            const seg = builder.segments[index];
            const point = endKind === 'from' ? seg.from : seg.to;
            const radius = Number(seg.radius) || builder.radius;
            const tolerance = Math.max(24, Math.min(90, radius * 0.65));
            const toleranceSq = tolerance * tolerance;
            const tubes = [];
            let blocking = false;
            for (let i = 0; i < builder.segments.length; i++) {
                if (i === index) continue;
                const other = builder.segments[i];
                if (!other?.from || !other?.to) continue;
                let otherEnd = null;
                if (distanceSq(point, other.from) <= toleranceSq) otherEnd = 'from';
                else if (distanceSq(point, other.to) <= toleranceSq) otherEnd = 'to';
                else continue;
                if (!segmentIsSweepableTube(other) || segmentUsesDistanceWallMapping(other)) {
                    blocking = true;
                    continue;
                }
                tubes.push({ index: i, endKind: otherEnd, seg: other });
            }
            return { tubes, blocking };
        }

        function uniqueSweepContinuation(index, endKind, textureId) {
            const { tubes, blocking } = sweepEndpointNeighbors(index, endKind);
            if (blocking || tubes.length !== 1) return null;
            const next = tubes[0];
            if (sweepTextureKey(next.seg) !== textureId) return null;
            if (textureUsesSectionMapping(getWallTextureEntry(next.seg.wallTextureId)) !==
                textureUsesSectionMapping(getWallTextureEntry(textureId))) {
                return null;
            }
            return next;
        }

        function collectSweepChainFrom(startIndex, used) {
            const startSeg = builder.segments[startIndex];
            if (!segmentIsSweepableTube(startSeg) || segmentUsesDistanceWallMapping(startSeg) || used.has(startIndex)) {
                return null;
            }
            const textureId = sweepTextureKey(startSeg);
            let index = startIndex;
            let lookEnd = 'from';
            const seen = new Set();
            while (true) {
                const mark = index + ':' + lookEnd;
                if (seen.has(mark)) break;
                seen.add(mark);
                const next = uniqueSweepContinuation(index, lookEnd, textureId);
                if (!next) break;
                index = next.index;
                lookEnd = next.endKind === 'from' ? 'to' : 'from';
            }
            const entries = [];
            let cur = index;
            let direction = lookEnd === 'from' ? 1 : -1;
            while (Number.isInteger(cur) && !used.has(cur)) {
                const seg = builder.segments[cur];
                if (!segmentIsSweepableTube(seg) || segmentUsesDistanceWallMapping(seg)) break;
                if (sweepTextureKey(seg) !== textureId) break;
                entries.push({ index: cur, seg, direction });
                used.add(cur);
                const outEnd = direction > 0 ? 'to' : 'from';
                const next = uniqueSweepContinuation(cur, outEnd, textureId);
                if (!next) break;
                cur = next.index;
                direction = next.endKind === 'from' ? 1 : -1;
            }
            return entries.length ? { textureId, entries } : null;
        }

        function collectDistanceSweepChunks(drawn) {
            const byRun = new Map();
            for (let i = 0; i < builder.segments.length; i++) {
                const seg = builder.segments[i];
                if (!segmentUsesDistanceWallMapping(seg) || !segmentIsSweepableTube(seg)) continue;
                const runId = String(seg.wallTextureRunId || '');
                const order = Number(seg.wallTextureRunOrder);
                if (!runId || !Number.isInteger(order)) continue;
                if (!byRun.has(runId)) byRun.set(runId, []);
                byRun.get(runId).push({ index: i, seg, order });
            }
            const chunks = [];
            for (const [runId, list] of byRun) {
                list.sort((a, b) => a.order - b.order);
                let start = 0;
                for (let i = 1; i <= list.length; i++) {
                    const split = i === list.length ||
                        list[i].order !== list[i - 1].order + 1 ||
                        sweepTextureKey(list[i].seg) !== sweepTextureKey(list[i - 1].seg);
                    if (!split) continue;
                    const slice = list.slice(start, i);
                    start = i;
                    if (!slice.some(item => drawn.has(item.index))) continue;
                    chunks.push({
                        kind: 'distance',
                        runId,
                        textureId: sweepTextureKey(slice[0].seg),
                        uvMode: 'distance',
                        entries: slice.map(item => ({
                            index: item.index,
                            seg: item.seg,
                            direction: Number(item.seg.wallTextureRunDirection) < 0 ? -1 : 1
                        }))
                    });
                }
            }
            return chunks;
        }

        function collectCorridorSweepChunks(drawList) {
            const drawn = new Set(drawList.map(entry => entry.index));
            const used = new Set();
            const chunks = collectDistanceSweepChunks(drawn);
            for (const chunk of chunks) {
                for (const entry of chunk.entries) used.add(entry.index);
            }
            for (const entry of drawList) {
                const chain = collectSweepChainFrom(entry.index, used);
                if (!chain) continue;
                const sectionMapped = textureUsesSectionMapping(getWallTextureEntry(chain.textureId));
                chunks.push({
                    kind: sectionMapped ? 'section' : 'tile',
                    textureId: chain.textureId,
                    uvMode: sectionMapped ? 'section' : 'tile',
                    entries: chain.entries
                });
            }
            return chunks;
        }

        function renderSweepTubesWebGL(drawList, covered, activeTexture) {
            const gl = tunnelWebGL.gl;
            const chunks = collectCorridorSweepChunks(drawList);
            for (const chunk of chunks) {
                const samples = buildSweepPathSamples(chunk.entries);
                const mesh = buildSweepTubeGpuMesh(
                    samples,
                    TUNNEL_WEBGL_RADIAL_SEGMENTS * 2,
                    chunk.uvMode
                );
                if (!mesh) continue;
                for (const entry of chunk.entries) covered.add(entry.index);
                const first = chunk.entries[0].seg;
                const textureEntry = getWallTextureEntry(first.wallTextureId);
                const texture = getWebGLTextureForSegment(first, textureEntry) || tunnelWebGL.texture;
                const model = tunnelWebGL.modelScratch;
                model.fill(0);
                model[0] = model[5] = model[10] = model[15] = 1;
                gl.uniformMatrix4fv(tunnelWebGL.uModel, false, model);
                gl.uniform1f(tunnelWebGL.uAlpha, segmentWallAlpha(first, 1));
                if (chunk.uvMode === 'distance') {
                    gl.uniform2f(tunnelWebGL.uTileScale, 1, 1);
                    gl.uniform1f(tunnelWebGL.uOffset, 0);
                    gl.uniform1f(tunnelWebGL.uUOffset, Number(first.wallTextureUOffset) || 0);
                } else if (chunk.uvMode === 'section') {
                    gl.uniform2f(tunnelWebGL.uTileScale, 1, 1);
                    gl.uniform1f(tunnelWebGL.uOffset, 0);
                    gl.uniform1f(tunnelWebGL.uUOffset, 0);
                } else {
                    gl.uniform2f(tunnelWebGL.uTileScale, TUNNEL_WEBGL_TILE_U, 1);
                    gl.uniform1f(tunnelWebGL.uOffset, tunnelWebGL.scroll);
                    gl.uniform1f(tunnelWebGL.uUOffset, 0);
                }
                if (texture !== activeTexture) {
                    gl.bindTexture(gl.TEXTURE_2D, texture);
                    activeTexture = texture;
                }
                bindCylinderGpuMesh(mesh);
                gl.drawElements(gl.TRIANGLES, mesh.indexCount, gl.UNSIGNED_SHORT, 0);
                tunnelWebGL.lastDrawCount += 1;
            }
            return activeTexture;
        }

