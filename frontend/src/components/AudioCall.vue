<script setup lang="ts">
import { ref, shallowRef, onMounted, onUnmounted } from 'vue'
//@ts-ignore
import AudioPicker from './AudioPicker.vue'
import {
    Room,
    RoomEvent,
    RemoteParticipant,
    LocalParticipant,
    Track,
    RemoteTrack,
    RemoteAudioTrack,
    LocalTrackPublication,
    createAudioAnalyser
} from 'livekit-client'

const room = shallowRef<Room | null>(null)
const isConnected = ref(false)
const participants = ref<{ sid: string; identity: string }[]>([])
const localParticipant = shallowRef<LocalParticipant | null>(null)
const isMicrophoneEnabled = ref(false)
const errorMessage = ref('')
const roomName = ref('')
const audioElements = ref<Map<string, HTMLAudioElement>>(new Map())
const audioPlaybackEnabled = ref(false)

// 实际测得 frequencyBinCount 为 1024 
const animateId = ref<number | null>(null)
const localAudioAnalyser = ref<AnalyserNode | null>(null)
const remoteAudioAnalyser = ref<AnalyserNode | null>(null)

const localVolumeFunc = ref<() => number>(() => 0)
const remoteVolumeFunc = ref<() => number>(() => 0)
const volumeData = ref<number>(0)

function animate() {
    if (localVolumeFunc.value && remoteVolumeFunc.value) {
        const localVolume = localVolumeFunc.value()
        const remoteVolume = remoteVolumeFunc.value()
        volumeData.value = Math.max(localVolume, remoteVolume)
    }

    // if (localAudioAnalyser.value && remoteAudioAnalyser.value) {

    //     const localData = new Uint8Array(frequencyBinCount)
    //     const remoteData = new Uint8Array(frequencyBinCount)

    //     localAudioAnalyser.value.getByteFrequencyData(localData)
    //     remoteAudioAnalyser.value.getByteFrequencyData(remoteData)

    //     const mixedData = new Uint8Array(frequencyBinCount)
    //     for (let i = 0; i < frequencyBinCount; i++) {

    //         mixedData[i] = Math.max(localData[i], remoteData[i])
    //     }
    //     waveformData.value = mixedData

    // }

    animateId.value = setTimeout(animate, 100)
}
animate()



// LiveKit 服务器配置

interface Message {
    id: string
    role: string
    content: string
}

const messages = ref<Message[]>([])

const createRoom = async () => {
    // 使用开发服务器的 token 生成接口
    const response = await fetch(`/api/createRoom`)
    const data = await response.json()
    return data
}

const connectToRoom = async () => {
    // try {
    room.value = new Room({
        adaptiveStream: true,
        dynacast: true,
        publishDefaults: {
            audioPreset: {
                maxBitrate: 64000,
            },
        },
    })
    room.value.registerTextStreamHandler('lk.transcription', async (reader, participantInfo) => {
        console.log({ reader, participantInfo })
        if (!reader.info || !reader.info.attributes) {
            return
        }
        const attributes = reader.info.attributes
        if (participantInfo.identity === "用户" && attributes['lk.transcription_final'] !== "true") {
            return
        }

        const id = reader.info.id
        const role = participantInfo.identity
        const content = ""
        const message = {
            id,
            role,
            content
        }
        messages.value.push(message)
        for await (const chunk of reader) {
            const message = messages.value.find(m => m.id === id)
            if (message) {
                message.content += chunk
            }
        }
    });

    // 监听房间事件
    room.value
        .on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
            console.log('ParticipantConnected', participant)
            participants.value.push({
                sid: participant.sid,
                identity: participant.identity
            })
        })
        .on(RoomEvent.LocalAudioSilenceDetected, (publication: LocalTrackPublication) => {
            console.log("LocalAudioSilenceDetected")
            console.log({ publication })
        })
        .on(RoomEvent.LocalTrackPublished, (localTrackPublication: LocalTrackPublication) => {
            const localAudioTrack = localTrackPublication.audioTrack
            if (localAudioTrack) {
                const { calculateVolume, analyser } = createAudioAnalyser(localAudioTrack)
                localAudioAnalyser.value = analyser
                localVolumeFunc.value = calculateVolume
            }

        })
        .on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
            participants.value = participants.value.filter((p) => p.sid !== participant.sid)
            // 清理音频元素
            const audioElement = audioElements.value.get(participant.sid)
            if (audioElement) {
                audioElement.pause()
                audioElement.remove()
                audioElements.value.delete(participant.sid)
            }
        })
        // @ts-ignore
        .on(RoomEvent.TrackSubscribed, (track: RemoteTrack, publication, participant: RemoteParticipant) => {
            console.log("TrackSubscribed")
            if (track.kind === Track.Kind.Audio) {
                handleAudioTrack(track as RemoteAudioTrack, participant.sid)
                const { calculateVolume,analyser } = createAudioAnalyser(track as RemoteAudioTrack)
                remoteAudioAnalyser.value = analyser
                remoteVolumeFunc.value = calculateVolume
            }
        })
        // @ts-ignore
        .on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack, publication, participant: RemoteParticipant) => {
            if (track.kind === Track.Kind.Audio) {
                const audioElement = audioElements.value.get(participant.sid)
                if (audioElement) {
                    audioElement.pause()
                    audioElement.remove()
                    audioElements.value.delete(participant.sid)
                }
            }
        })
        .on(RoomEvent.Connected, async () => {
            try {
                isConnected.value = true
                localParticipant.value = room.value?.localParticipant || null
                // 连接成功后启用麦克风
                if (localParticipant.value) {
                    await localParticipant.value.setMicrophoneEnabled(true)
                    isMicrophoneEnabled.value = true
                }
            } catch (error) {
                console.error('连接后启用麦克风失败:', error)
            }
        })
        .on(RoomEvent.Disconnected, () => {
            isConnected.value = false
            participants.value = []
            localParticipant.value = null
            isMicrophoneEnabled.value = false
            roomName.value = ''
            // 清理所有音频元素
            audioElements.value.forEach((audioElement) => {
                audioElement.pause()
                audioElement.remove()
            })
            audioElements.value.clear()
        })

    // 获取 token 并连接到房间
    const { token, room_name, url } = await createRoom()
    roomName.value = room_name


    await room.value.connect(url, token, {
        autoSubscribe: true,
    })
    // } catch (error) {
    //     console.error('连接房间失败:')
    //     console.error({error})
    //     errorMessage.value = `连接失败: ${error instanceof Error ? error.message : '未知错误'}`
    // }
}

const enableAudioPlayback = async () => {
    try {
        audioPlaybackEnabled.value = true
        // 尝试播放所有现有的音频元素
        for (const audioElement of audioElements.value.values()) {
            await audioElement.play()
        }
    } catch (error) {
        console.error('启用音频播放失败:', error)
    }
}

const handleAudioTrack = (track: RemoteAudioTrack, participantSid: string) => {
    try {
        // 创建音频元素
        const audioElement = track.attach() as HTMLAudioElement
        audioElement.autoplay = true
        // 设置 playsInline 属性（移动端需要）
        audioElement.setAttribute('playsinline', 'true')
        audioElement.volume = 1.0
        // 添加到页面中（隐藏）
        audioElement.style.display = 'none'
        document.body.appendChild(audioElement)

        // 存储音频元素引用
        audioElements.value.set(participantSid, audioElement)

        console.log(`音频轨道已连接并开始播放: ${participantSid}`)

        // 如果音频播放已启用，立即播放
        if (audioPlaybackEnabled.value) {
            audioElement.play().catch((error) => {
                console.warn('自动播放失败:', error)
            })
        } else {
            // 尝试自动播放，如果失败则需要用户交互
            audioElement.play().catch((error) => {
                console.warn('自动播放失败，需要用户交互启用音频播放:', error)
            })
        }
    } catch (error) {
        console.error('处理音频轨道失败:', error)
    }
}

const disconnectFromRoom = async () => {
    if (room.value) {
        await room.value.disconnect()
    }
}

const toggleMicrophone = async () => {
    try {
        if (room.value && localParticipant.value) {
            const newState = !isMicrophoneEnabled.value
            await localParticipant.value.setMicrophoneEnabled(newState)
            isMicrophoneEnabled.value = newState
        }
    } catch (error) {
        console.error('切换麦克风状态失败:', error)
    }
}

onMounted(() => {
    connectToRoom()
})

onUnmounted(() => {
    disconnectFromRoom()
})
</script>

<template>
    <div class="audio-call">
        <!-- 左侧面板：状态和控制 -->
        <div class="left-panel">
            <div class="status">
                状态: {{ isConnected ? '已连接' : '未连接' }}
            </div>

            <div v-if="roomName" class="room-info">
                房间名称: {{ roomName }}
            </div>

            <div v-if="errorMessage" class="error">
                {{ errorMessage }}
            </div>
            
            <AudioPicker :volume="volumeData" />

            <div class="controls">
                <button @click="toggleMicrophone">
                    {{ isMicrophoneEnabled ? '关闭麦克风' : '开启麦克风' }}
                </button>

                <button v-if="!audioPlaybackEnabled && audioElements.size > 0" @click="enableAudioPlayback"
                    class="audio-enable-btn">
                    启用音频播放 ({{ audioElements.size }} 个音频源)
                </button>
            </div>

            <div v-if="audioElements.size > 0" class="audio-status">
                <h4>音频状态</h4>
                <div class="audio-info">
                    正在播放 {{ audioElements.size }} 个音频流
                    <span v-if="audioPlaybackEnabled" class="status-enabled">✓ 已启用</span>
                    <span v-else class="status-disabled">⚠ 需要用户交互启用</span>
                </div>
            </div>

            <div class="participants">
                <h3>参与者列表</h3>
                <div v-if="localParticipant" class="participant local">
                    我 (本地)
                </div>
                <div v-for="participant in participants" :key="participant.sid" class="participant">
                    {{ participant.identity }}
                </div>
            </div>
        </div>

        <!-- 右侧面板：对话消息 -->
        <div class="right-panel">
            <div v-for="message in messages" :key="message.id" class="message" :class="message.role">
                <div class="message-content">
                    {{ JSON.stringify(message) }}
                </div>
            </div>

        </div>
    </div>
</template>

<style scoped>
.audio-call {
    display: flex;
    height: 100vh;
    max-width: 1400px;
    min-width: 100vh;
    margin: 0 auto;
    gap: 20px;
    padding: 20px;
    text-align: center;
}

/* 左侧面板样式 */
.left-panel {
    flex: 0 0 400px;
    background-color: #f8f9fa;
    border-radius: 12px;
    padding: 20px;
    overflow-y: auto;
}

/* 右侧面板样式 */
.right-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    background-color: #ffffff;
    border-radius: 12px;
    border: 1px solid #e0e0e0;
    overflow-y: auto;
}

/* 聊天头部 */
.chat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px;
    background-color: #f8f9fa;
    border-bottom: 1px solid #e0e0e0;
}

.chat-header h3 {
    margin: 0;
    color: #333;
}

.clear-all-btn {
    padding: 8px 16px;
    background-color: #f44336;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
}

.clear-all-btn:hover {
    background-color: #d32f2f;
}

/* 聊天容器 */
.chat-container {
    flex: 1;
    padding: 20px;
    overflow-y: auto;
    background-color: #fafafa;
}

/* 空聊天状态 */
.empty-chat {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #9e9e9e;
}

.empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
}

.empty-text {
    font-size: 18px;
    font-weight: 500;
}

/* 消息样式 */
.message {
    display: flex;
    margin-bottom: 16px;
    animation: fadeIn 0.3s ease-in;
}

.message.transcription {
    justify-content: flex-start;
}

.message.llm_response {
    justify-content: flex-start;
}

.message-avatar {
    flex-shrink: 0;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    margin-right: 12px;
}

.message.transcription .message-avatar {
    background-color: #e3f2fd;
}

.message.llm_response .message-avatar {
    background-color: #e8f5e8;
}

.message-content {
    flex: 1;
    max-width: 70%;
}

.message-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}

.message-sender {
    font-weight: 600;
    font-size: 14px;
}

.message.transcription .message-sender {
    color: #1976d2;
}

.message.llm_response .message-sender {
    color: #388e3c;
}

.message-time {
    font-size: 12px;
    color: #9e9e9e;
}

.message-text {
    background-color: white;
    padding: 12px 16px;
    border-radius: 12px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    line-height: 1.4;
    color: #333;
}

.message.transcription .message-text {
    border-left: 3px solid #2196F3;
}

.message.llm_response .message-text {
    border-left: 3px solid #4CAF50;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* 左侧面板内容样式 */
.status {
    margin-bottom: 20px;
    padding: 12px;
    background-color: #ffffff;
    border-radius: 8px;
    border-left: 4px solid #2196F3;
    font-weight: 500;
}

.room-info {
    margin-bottom: 20px;
    padding: 12px;
    background-color: #e8f5e8;
    border-radius: 8px;
    border-left: 4px solid #4CAF50;
}

.error {
    margin-bottom: 20px;
    padding: 12px;
    background-color: #ffebee;
    color: #c62828;
    border-radius: 8px;
    border-left: 4px solid #f44336;
}

.controls {
    margin-bottom: 20px;
}

.controls button {
    padding: 12px 20px;
    background-color: #4CAF50;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    margin-right: 10px;
    margin-bottom: 10px;
    font-weight: 500;
    transition: background-color 0.2s;
}

.controls button:hover {
    background-color: #45a049;
}

.audio-enable-btn {
    background-color: #2196F3 !important;
}

.audio-enable-btn:hover {
    background-color: #1976D2 !important;
}

.participants {
    margin-top: 20px;
}

.participants h3 {
    margin-bottom: 12px;
    color: #333;
}

.participant {
    padding: 12px;
    margin: 8px 0;
    background-color: #ffffff;
    border-radius: 8px;
    border-left: 3px solid #e0e0e0;
}

.participant.local {
    background-color: #e3f2fd;
    border-left-color: #2196F3;
}

.audio-status {
    margin-top: 20px;
    padding: 12px;
    background-color: #ffffff;
    border-radius: 8px;
}

.audio-status h4 {
    margin: 0 0 8px 0;
    color: #333;
}

.audio-info {
    padding: 8px;
    background-color: #e8f5e8;
    border-radius: 6px;
    border-left: 3px solid #4CAF50;
    font-size: 14px;
}

.status-enabled {
    color: #4CAF50;
    font-weight: 600;
}

.status-disabled {
    color: #f44336;
    font-weight: 600;
}

/* 响应式设计 */
@media (max-width: 768px) {
    .audio-call {
        flex-direction: column;
        height: auto;
        padding: 10px;
    }

    .left-panel {
        flex: none;
        margin-bottom: 20px;
    }

    .right-panel {
        height: 60vh;
    }
}
</style>