from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import argparse
import uuid
from livekit import api
from livekit.api import LiveKitAPI, CreateRoomRequest


app = FastAPI()

# LiveKit 配置 - 将通过命令行参数设置
LIVEKIT_API_KEY = None
LIVEKIT_API_SECRET = None
LIVEKIT_HOST = None


class TokenResponse(BaseModel):
    url: str
    room_name: str
    token: str
    
    
def create_token(user_name:str,room_name: str) -> str:
    token =  api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)\
        .with_identity(user_name)\
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name
            ))
    return token.to_jwt()

async def create_room(room_name: str) -> None:
    url = LIVEKIT_HOST
    api_key = LIVEKIT_API_KEY
    api_secret = LIVEKIT_API_SECRET  
    
    async with LiveKitAPI(url=url,api_key=api_key,api_secret=api_secret) as lkapi:
        await lkapi.room.create_room(CreateRoomRequest(
            name=room_name,
            max_participants=2
            ))
        
@app.get("/api/createRoom")
async def createRoom() -> TokenResponse:
    room_name = str(uuid.uuid4())
    
    try:
        token = create_token("用户",room_name)
        await create_room(room_name)
        return TokenResponse(room_name=room_name, token=token, url=LIVEKIT_HOST)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
# @app.get("/api/createRoom", response_model=TokenResponse)
# async def create_room():
#     room_name = str(uuid.uuid4())
    
#     try:
#         # 创建 LiveKit 访问令牌
#         token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)\
#             .with_identity("用户")\
#             .with_grants(
#                 api.VideoGrants(
#                     room_join=True,
#                     room=room_name
#                 )
#             )
            
#         token_str = token.to_jwt()
#         print(LIVEKIT_HOST)
#         return TokenResponse(room_name=room_name, token=token_str, url=LIVEKIT_HOST)
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


def parse_args():
    parser = argparse.ArgumentParser(description='LiveKit 实时语音演示后端服务')
    parser.add_argument('--host', required=True, help='LiveKit 服务器地址 (例如: ws://localhost:7880)')
    parser.add_argument('--api-key', required=True, help='LiveKit API Key')
    parser.add_argument('--api-secret', required=True, help='LiveKit API Secret')
    return parser.parse_args()


if __name__ == "__main__":
    import uvicorn
    
    # 解析命令行参数
    args = parse_args()
    
    # 设置全局配置
    LIVEKIT_HOST = args.host
    LIVEKIT_API_KEY = args.api_key
    LIVEKIT_API_SECRET = args.api_secret
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
