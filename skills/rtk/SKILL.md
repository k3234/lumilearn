---
name: rtk
version: "1.0.0"
description: RTK (Redux Toolkit) AI 编程优化技能 - 提供 React/Redux 状态管理的最佳实践和代码生成
tags:
  - react
  - redux
  - state-management
  - frontend
  - typescript
author: LumiLearn Team
license: Apache-2.0
---

# RTK - Redux Toolkit AI 编程优化技能

## 概述

本技能专为 LumiLearn 模型设计，提供 Redux Toolkit (RTK) 的最佳实践、代码模板和优化建议。帮助开发者快速构建可维护的 React 状态管理代码。

## 适用场景

- React 应用状态管理设计
- Redux Store 架构规划
- RTK Query 数据获取
- TypeScript 类型安全的状态管理
- 性能优化和最佳实践

## 核心功能

### 1. Store 配置生成

根据应用需求自动生成完整的 Store 配置：

```typescript
// 生成的 Store 结构
import { configureStore } from '@reduxjs/toolkit'
import { setupListeners } from '@reduxjs/toolkit/query'
import { apiSlice } from './apiSlice'

export const store = configureStore({
  reducer: {
    [apiSlice.reducerPath]: apiSlice.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(apiSlice.middleware),
})

setupListeners(store.dispatch)
```

### 2. Slice 自动生成

根据实体模型自动生成 CRUD Slice：

```typescript
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'

// 自动生成完整的 Slice 代码
const userSlice = createSlice({
  name: 'users',
  initialState: { entities: {}, ids: [], loading: 'idle' },
  reducers: {
    // CRUD 操作
  },
  extraReducers: (builder) => {
    // 异步处理
  }
})
```

### 3. RTK Query API 生成

自动生成类型安全的 API 客户端：

```typescript
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'

export const api = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({ baseUrl: '/api' }),
  tagTypes: ['User', 'Post'],
  endpoints: (builder) => ({
    getUsers: builder.query<User[], void>({
      query: () => 'users',
      providesTags: ['User']
    }),
    // 更多端点...
  })
})
```

## 使用指南

### 基本用法

当用户需要 Redux 相关代码时：

1. **分析需求** - 确定应用规模、数据流复杂度
2. **生成架构** - 提供 Store + Slice + API 的完整方案
3. **类型安全** - 确保 TypeScript 类型完整
4. **性能优化** - 添加 memoization 和代码分割建议

### 代码模板

#### 小型应用模板

```typescript
// store.ts - 轻量级配置
import { configureStore } from '@reduxjs/toolkit'
import counterReducer from './counterSlice'

export const store = configureStore({
  reducer: {
    counter: counterReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
```

#### 大型应用模板

```typescript
// store.ts - 企业级配置
import { configureStore, combineReducers } from '@reduxjs/toolkit'
import { persistStore, persistReducer } from 'redux-persist'
import storage from 'redux-persist/lib/storage'

const rootReducer = combineReducers({
  auth: authReducer,
  users: usersReducer,
  [api.reducerPath]: api.reducer,
})

const persistedReducer = persistReducer(
  { key: 'root', storage, whitelist: ['auth'] },
  rootReducer
)

export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefault) =>
    getDefault({ serializableCheck: false })
      .concat(api.middleware),
})
```

## 最佳实践

### 1. 状态设计原则

- **扁平化结构** - 避免深层嵌套
- **规范化数据** - 使用 ID 引用而非嵌套对象
- **最小化状态** - 派生数据使用 selectors

### 2. 性能优化

```typescript
// 使用 createSelector 进行记忆化
import { createSelector } from '@reduxjs/toolkit'

const selectUsers = (state: RootState) => state.users.entities
const selectUserIds = (state: RootState) => state.users.ids

export const selectActiveUsers = createSelector(
  [selectUsers, selectUserIds],
  (users, ids) => ids.map(id => users[id]).filter(u => u.isActive)
)
```

### 3. 异步处理模式

```typescript
// 使用 createAsyncThunk
export const fetchUserById = createAsyncThunk(
  'users/fetchById',
  async (userId: string, { rejectWithValue }) => {
    try {
      const response = await api.getUser(userId)
      return response.data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)
```

## 集成到 LumiLearn

### API 端点

```
POST /api/skills/rtk/generate
{
  "app_type": "small|medium|large",
  "entities": ["User", "Post", "Comment"],
  "features": ["auth", "caching", "offline"],
  "typescript": true
}
```

### 响应格式

```json
{
  "store": "// store.ts 代码",
  "slices": ["// slice 代码数组"],
  "api": "// RTK Query API 代码",
  "hooks": "// 自定义 hooks",
  "setup": "// 安装和配置说明"
}
```

## 示例

### 示例 1: 电商应用状态管理

```
用户: 我需要为电商应用设计 Redux 状态管理

AI: 基于您的需求，我推荐以下架构：

1. Store 结构:
   - auth: 用户认证
   - cart: 购物车
   - products: 商品列表
   - orders: 订单管理
   - ui: UI 状态

2. 生成的代码:
   [提供完整的 TypeScript 代码]

3. 性能优化:
   - 购物车使用 normalized state
   - 商品列表使用 RTK Query 缓存
   - 图片懒加载状态管理
```

### 示例 2: 实时协作应用

```
用户: 如何实现实时协作的文档编辑器状态管理？

AI: 针对实时协作场景，建议：

1. 使用 RTK Query + WebSocket
2. Optimistic Updates 策略
3. 冲突解决机制
4. 离线优先架构

[提供完整代码实现]
```

## 相关资源

- [Redux Toolkit 官方文档](https://redux-toolkit.js.org/)
- [RTK Query 指南](https://redux-toolkit.js.org/rtk-query/overview)
- [最佳实践博客](https://redux.js.org/style-guide/)

## 更新日志

### v1.0.0 (2026-05-21)
- 初始版本
- 支持基础 Store 生成
- 支持 Slice CRUD 生成
- 支持 RTK Query API 生成
- 集成到 LumiLearn API
