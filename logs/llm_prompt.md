# LLM调用日志

本文件记录每个会话中各步骤调用大模型时的完整上下文和提示词。

---

*****会话ID: 98708e37-1304-49b0-89a4-373cb730367f | 问题: 盘石头水库和小南海水库相比，哪个当前水位高？*****

## 意图分析 (Planner.analyze_intent)
**时间**: 2025-12-26 11:37:33
**提示词模板**: INTENT_ANALYSIS_PROMPT

**上下文变量**:
- context_summary: 无
- chat_history: 无
- user_message: 盘石头水库和小南海水库相比，哪个当前水位高？

**完整提示词**:
```
你是卫共流域数字孪生系统的智能助手"小卫"，负责分析用户意图。

## 用户意图类别
1. general_chat - 一般对话、闲聊（如问候、感谢、闲聊、询问你的信息等）
2. knowledge_qa - 流域知识问答（关于流域概况、水利设施、防洪知识、监测站点、历时洪水、调度预案、工程治理、系统功能、专业模型等）
3. data_query - 监测数据查询（获取水情、雨情、水位、流量、视频等实时或历史监测数据）
4. flood_forecast - 洪水预报（进行洪水预报、查询预报结果、查询预警信息、查询洪水风险、获取预报边界条件等）
5. flood_simulation - 洪水预演（进行洪水预演、查询预演结果、查询预警信息、查询洪水风险、获取预演边界条件等）
6. emergency_plan - 预案生成（防洪应急预案）
7. damage_assessment - 灾损评估、避险转移等业务

## 上下文信息
对话历史摘要: 无

最近对话:
无

## 用户当前消息
盘石头水库和小南海水库相比，哪个当前水位高？

## 输出要求
请分析用户意图，返回JSON格式:

**如果是 general_chat（一般对话/闲聊），请直接生成回复内容：**
{
    "intent": "general_chat",
    "confidence": 0.95,
    "direct_response": "你的友好回复内容（控制在100字以内）",
    "output_type": "text"
}

**如果是其他业务意图，返回：**
{
    "intent": "意图类别",
    "confidence": 0.95,
    "entities": {"提取的关键实体": "值"},
    "requires_data_query": true/false,
    "requires_model_call": true/false,
    "output_type": "text 或 web_page"
}

注意:
- 对于一般对话，你需要友好地回复用户，可以简要介绍自己的能力（流域介绍、工程信息查询、实时水雨情查询、洪水预报预演及应急预案生成等）
- 如果涉及图表展示（如水位趋势图、雨量分布图等），output_type应为"web_page"
- 如果只是简单文字回答，output_type应为"text"

```

**LLM响应**:
```
{'intent': 'data_query', 'confidence': 0.98, 'entities': {'locations': ['盘石头水库', '小南海水库'], 'data_type': '水位', 'time': '当前'}, 'requires_data_query': True, 'requires_model_call': False, 'output_type': 'text'}
```

## 计划生成 (Planner.generate_plan)
**时间**: 2025-12-26 11:37:45
**提示词模板**: PLAN_GENERATION_PROMPT

**上下文变量**:
- available_tools: 1. 工具名称: login_basin_system
描述: 登录卫共流域数字孪生系统，获取访问令牌(Token)。通常在需要鉴权的接口调用前执行。
类别: basin_info
参数:
  - account [string] (可选): 登录账号，可选，默认使用系统配置
  - password [string] (可选): 登录密码，可选，默认使用系统配置
  - force_refresh [boolean] (可选): 是否强制刷新Token

2. 工具名称: get_map_data
描述: 查询各类地理要素的地图数据（包含空间坐标），支持测站、水库、蓄滞洪区、分洪闸堰等类型
类别: basin_info
参数:
  - ref_table [string] (必需): 数据表名: geo_st_base(测站), geo_res_base(水库), geo_fld_stor(蓄滞洪区), geo_flo_dam(分洪闸堰)
  - filter_field [string] (可选): 查询字段名。水库使用stcd(编码)和res_name(名称)；测站、蓄滞洪区、分...(已截断)
- available_workflows: 
1. flood_forecast_workflow - 洪水预报工作流
   触发条件: 用户询问洪水预报相关问题
   
2. flood_simulation_workflow - 洪水预演工作流
   触发条件: 用户要求进行洪水模拟

3. emergency_plan_workflow - 应急预案工作流
   触发条件: 用户需要生成防洪预案

4. latest_flood_forecast_query - 最新洪水预报结果查询
   触发条件: 用户询问最新预报结果

- rag_context: 以下是相关的知识库内容：

[1] (监测设施)
水文监测站网是水文信息采集的基础设施，包括：
                - 水位站：监测河道、水库水位变化
                - 雨量站：监测降雨量和降雨强度
                - 流量站：监测河道流量
                - 水质站：监测水体水质指标
                卫共流域共有各类水文监测站点约200个，实现了重点区域全覆盖。

[2] (专业知识)
洪水预报是根据实测和预报的水文气象资料，应用水文学方法，
                对未来一定时期内的洪水过程进行预测。主要方法包括：
                1. 降雨径流预报：根据降雨量预测径流量
                2. 河道洪水演进：利用马斯京根法等计算洪水传播
                3. 水库调度：考虑水库调蓄作用优化泄洪方案
                预报精度受数据质量、模型参数等因素影响。

[3] (防洪知识)
防洪预警等级分为四级：
                ...(已截断)
- intent: data_query
- entities: {'locations': ['盘石头水库', '小南海水库'], 'data_type': '水位', 'time': '当前'}
- user_message: 盘石头水库和小南海水库相比，哪个当前水位高？

**完整提示词**:
```
你是卫共流域数字孪生系统的任务规划器，负责制定执行计划。

## 可用工具
1. 工具名称: login_basin_system
描述: 登录卫共流域数字孪生系统，获取访问令牌(Token)。通常在需要鉴权的接口调用前执行。
类别: basin_info
参数:
  - account [string] (可选): 登录账号，可选，默认使用系统配置
  - password [string] (可选): 登录密码，可选，默认使用系统配置
  - force_refresh [boolean] (可选): 是否强制刷新Token

2. 工具名称: get_map_data
描述: 查询各类地理要素的地图数据（包含空间坐标），支持测站、水库、蓄滞洪区、分洪闸堰等类型
类别: basin_info
参数:
  - ref_table [string] (必需): 数据表名: geo_st_base(测站), geo_res_base(水库), geo_fld_stor(蓄滞洪区), geo_flo_dam(分洪闸堰)
  - filter_field [string] (可选): 查询字段名。水库使用stcd(编码)和res_name(名称)；测站、蓄滞洪区、分洪闸堰使用code(编码)和name(名称)
  - filter_operator [string] (可选): 关系运算符: =, in, like, >, <
  - filter_value [string] (可选): 查询值，只能有一个

3. 工具名称: get_list_data
描述: 查询各类要素的列表数据（不含空间坐标），如水库防洪责任人扩展信息
类别: basin_info
参数:
  - ref_table [string] (必需): 数据表名，如geo_res_flood_ext(水库防洪责任人扩展信息)
  - filter_field [string] (可选): 查询字段名
  - filter_operator [string] (可选): 关系运算符: =, in, like
  - filter_value [string] (可选): 查询值

4. 工具名称: get_reservoir_info
描述: 查询水库的基础属性信息，包括位置、工程等级、流域面积、库容、校核洪水位等
类别: basin_info
参数:
  - stcd [string] (可选): 测站编码，可选，不传则查询所有水库

5. 工具名称: get_reservoir_flood_detail
描述: 查询单个水库的防洪特征值详情，包括校核洪水位、设计洪水位、正常蓄水位、死水位、库容等
类别: basin_info
参数:
  - stcd [string] (必需): 测站编码（必填）

6. 工具名称: get_reservoir_flood_list
描述: 获取所有水库的防洪特征值信息列表，包含各水库的校核洪水位、设计洪水位、正常蓄水位、库容等
类别: basin_info
参数:
  无参数

7. 工具名称: get_sluice_info
描述: 查询水闸的基础属性信息，包括位置、河流名称、工程规模、设计流量等
类别: basin_info
参数:
  - stcd [string] (可选): 测站编码，可选，不传则查询所有水闸

8. 工具名称: get_flood_dam_info
描述: 查询分洪闸堰的基础信息，包括位置、设计分洪流量等
类别: basin_info
参数:
  - name [string] (可选): 分洪闸堰名称，可选，支持模糊查询

9. 工具名称: get_flood_storage_area
描述: 查询蓄滞洪区的基础信息，包括面积、进洪设施、设计蓄洪库容、设计蓄洪水位等
类别: basin_info
参数:
  - name [string] (可选): 蓄滞洪区名称，可选，支持模糊查询

10. 工具名称: get_river_flood_list
描述: 获取所有河道测站的防洪特征值信息列表，包括警戒水位、保证水位、左右堤高程、实测最高水位等
类别: basin_info
参数:
  无参数

11. 工具名称: get_station_list
描述: 按测站类型查询测站的基础信息列表，包括测站编码、名称、位置、河流名称等
类别: basin_info
参数:
  - sttp [string] (必需): 测站类型: ZQ(水文站), ZZ(水位站), PP(雨量站), RR(水库站), DD(闸坝站), ZB(水位遥测站), AI(智能监测站)

12. 工具名称: get_camera_list
描述: 获取视频监控摄像头列表，包括摄像头编码、名称、关联测站、视频流地址等
类别: basin_info
参数:
  - stcd [string] (可选): 测站编码，可选，不传则查询所有摄像头

13. 工具名称: get_drone_project_list
描述: 查询无人机项目列表，获取项目ID和项目名称
类别: basin_info
参数:
  无参数

14. 工具名称: get_drone_device_list
描述: 查询无人机设备列表，获取设备序列号、名称、类型、状态等信息
类别: basin_info
参数:
  无参数

15. 工具名称: get_remote_sensing_task_list
描述: 查询遥感监测任务列表，支持洪涝水淹、洪涝监测、水利工程变形、小流域监测等任务类型
类别: basin_info
参数:
  - task_type [string] (必需): 任务类型: HHSL(洪涝水淹), HLJC(洪涝监测), SLGCBX(水利工程变形), XDMJC(小流域监测)
  - task_name [string] (可选): 任务名称，支持模糊查询
  - page [integer] (必需): 页码，从1开始
  - limit [integer] (必需): 每页条数
  - user_id [string] (必需): 用户ID

16. 工具名称: query_rain_process
描述: 根据测站编码和时间范围查询雨量历史过程数据，返回时段降水量、日降水量、累计降水量等信息
类别: hydro_monitor
参数:
  - stcd [string] (必需): 测站编码
  - search_begin_time [string] (必需): 查询开始时间，格式：yyyy-MM-dd HH:mm:ss
  - search_end_time [string] (必需): 查询结束时间，格式：yyyy-MM-dd HH:mm:ss

17. 工具名称: query_rain_statistics
描述: 根据测站编码查询雨量统计数据，返回1小时、3小时、6小时、12小时、24小时等多时段的雨量统计信息
类别: hydro_monitor
参数:
  - stcd [string] (必需): 测站编码

18. 工具名称: query_rain_sum
描述: 根据时间范围查询所有测站的雨量累计数据，返回测站编码、名称、累计降水量、测站位置等信息
类别: hydro_monitor
参数:
  - search_begin_time [string] (必需): 查询开始时间，格式：yyyy-MM-dd HH:mm:ss
  - search_end_time [string] (必需): 查询结束时间，格式：yyyy-MM-dd HH:mm:ss

19. 工具名称: query_reservoir_last
描述: 获取水库的最新实时水情数据，可以指定水库测站编码，包括库水位、蓄水量、入库流量、出库流量等信息
类别: hydro_monitor
参数:
  - stcd [string] (可选): 测站编码（可选，不传则查询所有水库）

20. 工具名称: query_reservoir_process
描述: 根据测站编码和时间范围查询水库的历史水情过程数据，返回库水位、蓄水量、入库流量、出库流量等时序数据
类别: hydro_monitor
参数:
  - stcd [string] (必需): 测站编码
  - search_begin_time [string] (必需): 查询开始时间，格式：yyyy-MM-dd HH:mm:ss
  - search_end_time [string] (必需): 查询结束时间，格式：yyyy-MM-dd HH:mm:ss

21. 工具名称: query_river_last
描述: 获取河道测站的最新实时水情数据，可以指定河道测站编码，包括水位、流量、水势、告警级别等信息
类别: hydro_monitor
参数:
  - stcd [string] (可选): 测站编码（可选，不传则查询所有河道）

22. 工具名称: query_river_process
描述: 根据测站编码和时间范围查询河道水情历史过程数据，返回水位、流量、水势等时序数据
类别: hydro_monitor
参数:
  - stcd [string] (必需): 测站编码
  - search_begin_time [string] (必需): 查询开始时间，格式：yyyy-MM-dd HH:mm:ss
  - search_end_time [string] (必需): 查询结束时间，格式：yyyy-MM-dd HH:mm:ss

23. 工具名称: query_ai_water_last
描述: 获取AI智能监测设备的最新水情数据，返回测站编码、名称、水位、数据时间等信息
类别: hydro_monitor
参数:
  无参数

24. 工具名称: query_ai_water_process
描述: 根据测站编码和时间范围查询AI智能监测设备的水情历史过程数据
类别: hydro_monitor
参数:
  - stcd [string] (必需): 测站编码
  - st [string] (必需): 开始时间，格式：yyyy-MM-dd HH:mm:ss
  - ed [string] (必需): 结束时间，格式：yyyy-MM-dd HH:mm:ss

25. 工具名称: query_ai_rain_last
描述: 获取AI智能监测设备的最新雨量数据，返回测站编码、名称、时段降水量、数据时间等信息
类别: hydro_monitor
参数:
  无参数

26. 工具名称: query_ai_rain_process
描述: 根据测站编码和时间范围查询AI智能监测设备的雨量历史过程数据
类别: hydro_monitor
参数:
  - stcd [string] (必需): 测站编码
  - st [string] (必需): 开始时间，格式：yyyy-MM-dd HH:mm:ss
  - ed [string] (必需): 结束时间，格式：yyyy-MM-dd HH:mm:ss

27. 工具名称: query_camera_preview
描述: 根据摄像头编码获取实时视频预览流地址
类别: hydro_monitor
参数:
  - code [string] (必需): 摄像头编码

28. 工具名称: query_sensor_data_process
描述: 根据传感器ID和时间范围查询传感器的历史监测数据
类别: hydro_monitor
参数:
  - sensor_id [string] (必需): 传感器ID
  - st [string] (必需): 开始时间，格式：yyyy-MM-dd HH:mm:ss
  - ed [string] (必需): 结束时间，格式：yyyy-MM-dd HH:mm:ss

29. 工具名称: query_drone_status
描述: 查询大疆无人机设备的实时状态，包括设备序列号、状态、电量、位置等信息
类别: hydro_monitor
参数:
  - device_sn [string] (必需): 无人机设备序列号

30. 工具名称: send_sms
描述: 发送告警短信通知，需要提供接收手机号码和短信内容
类别: hydro_monitor
参数:
  - phone [string] (必需): 接收短信的手机号码
  - content [string] (必需): 短信内容

31. 工具名称: model_plan_add
描述: 新增洪水预报模拟方案，设置方案名称、时间范围、业务模型等参数
类别: flood_control
参数:
  - plan_name [string] (必需): 方案名称
  - business_code [string] (必需): 业务模型编码
  - start_time [string] (必需): 开始时间，格式: yyyy-MM-dd HH:mm:ss
  - end_time [string] (必需): 结束时间，格式: yyyy-MM-dd HH:mm:ss
  - plan_desc [string] (可选): 方案描述
  - business_name [string] (可选): 业务模型名称
  - step_save_minutes [integer] (可选): 模型结果保存时间步长(分钟)
  - inherit_plan_code [string] (可选): 继承方案的编码
  - view_point [string] (可选): 相机位置
  - model_object [string] (可选): 模型参数JSON字符串

32. 工具名称: model_plan_edit
描述: 编辑已存在的洪水预报模拟方案
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码
  - plan_name [string] (可选): 方案名称
  - business_code [string] (可选): 业务模型编码
  - start_time [string] (可选): 开始时间，格式: yyyy-MM-dd HH:mm:ss
  - end_time [string] (可选): 结束时间，格式: yyyy-MM-dd HH:mm:ss
  - plan_desc [string] (可选): 方案描述
  - business_name [string] (可选): 业务模型名称
  - step_save_minutes [integer] (可选): 模型结果保存时间步长(分钟)
  - inherit_plan_code [string] (可选): 继承方案的编码
  - view_point [string] (可选): 相机位置
  - model_object [string] (可选): 模型参数JSON字符串

33. 工具名称: model_plan_delete
描述: 删除指定的洪水预报模拟方案
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

34. 工具名称: model_plan_detail
描述: 根据方案编码查看模拟方案的详细信息
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

35. 工具名称: model_plan_state
描述: 查看模拟方案的当前计算状态
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

36. 工具名称: model_plan_list_all
描述: 查询全部洪水预报模拟方案列表(不分页)，支持按方案名称、编码、状态等条件筛选
类别: flood_control
参数:
  - plan_code [string] (可选): 方案编码（精确匹配）
  - plan_name [string] (可选): 方案名称（模糊查询）
  - business_code [string] (可选): 业务模型编码
  - state [string] (可选): 计算状态：待计算/计算中/计算完成/计算失败

37. 工具名称: model_plan_calc
描述: 启动指定方案的洪水预报模型计算
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

38. 工具名称: model_plan_stop
描述: 终止正在进行的模拟方案计算
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

39. 工具名称: model_plan_progress
描述: 获取模拟方案的计算进度信息
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

40. 工具名称: model_plan_count_state
描述: 获取不同计算状态的方案数量统计
类别: flood_control
参数:
  无参数

41. 工具名称: model_plan_count_plan
描述: 获取各业务模型的模拟方案数量统计
类别: flood_control
参数:
  无参数

42. 工具名称: model_plan_auto_forecast
描述: 手动触发一次自动洪水预报计算（无需登录）
类别: flood_control
参数:
  无参数

43. 工具名称: model_basic_list_all
描述: 查询全部基础模型列表(不分页)，支持按模型名称、编码、类型等条件筛选
类别: flood_control
参数:
  - name [string] (可选): 模型名称
  - code [string] (可选): 模型编码
  - type_id [integer] (可选): 模型类型ID

44. 工具名称: model_basic_detail
描述: 根据模型ID查看基础模型的详细信息，包括模型介绍、原理、参数等
类别: flood_control
参数:
  - id [integer] (必需): 模型ID

45. 工具名称: model_basic_count
描述: 获取基础模型、模型实例、业务模型、模拟方案的数量统计
类别: flood_control
参数:
  无参数

46. 工具名称: model_instance_list_all
描述: 查询全部模型实例列表(不分页)，支持按实例名称、编码、基础模型、流域等条件筛选
类别: flood_control
参数:
  - name [string] (可选): 实例名称
  - code [string] (可选): 实例编码
  - basic_code [string] (可选): 基础模型编码
  - basin_code [string] (可选): 流域编码

47. 工具名称: model_instance_detail
描述: 根据实例ID查看模型实例的详细信息
类别: flood_control
参数:
  - id [integer] (必需): 实例ID

48. 工具名称: model_business_list_all
描述: 查询全部业务模型列表(不分页)，支持按业务模型名称、编码、类型等条件筛选
类别: flood_control
参数:
  - name [string] (可选): 业务模型名称
  - code [string] (可选): 业务模型编码
  - type_id [integer] (可选): 业务模型类型ID

49. 工具名称: model_business_add
描述: 新增业务模型，设置业务模型名称、编码、类型等参数
类别: flood_control
参数:
  - name [string] (必需): 业务模型名称
  - code [string] (必需): 业务模型编码（唯一）
  - type_id [integer] (可选): 业务模型类型ID
  - type_name [string] (可选): 业务模型类型名称
  - instance_codes [string] (可选): 模型实例编码(多个用逗号分隔)
  - view_point [string] (可选): 相机位置
  - url [string] (可选): 模型地址
  - remark [string] (可选): 备注

50. 工具名称: model_business_detail
描述: 根据业务模型编码查看业务模型的详细信息
类别: flood_control
参数:
  - code [string] (必需): 业务模型编码

51. 工具名称: forecast_rain_ecmwf_avg
描述: 获取流域平均的格网预报降雨过程(无需登录)，返回时序降雨数据
类别: flood_control
参数:
  - st [string] (必需): 开始时间，格式: yyyy-MM-dd HH:mm:ss
  - ed [string] (必需): 结束时间，格式: yyyy-MM-dd HH:mm:ss
  - business_code [string] (可选): 业务模型编码

52. 工具名称: forecast_rain_ecmwf_each
描述: 获取各子流域的格网预报降雨过程，返回按子流域编码分组的降雨时序数据
类别: flood_control
参数:
  - st [string] (必需): 开始时间，格式: yyyy-MM-dd HH:mm:ss
  - ed [string] (必需): 结束时间，格式: yyyy-MM-dd HH:mm:ss
  - business_code [string] (可选): 业务模型编码

53. 工具名称: forecast_rain_ecmwf_rect
描述: 获取矩形区域内的格网预报降雨过程，通过经纬度范围指定区域
类别: flood_control
参数:
  - st [string] (必需): 开始时间
  - ed [string] (必需): 结束时间
  - xmin [float] (必需): 矩形左边界经度
  - xmax [float] (必需): 矩形右边界经度
  - ymin [float] (必需): 矩形下边界纬度
  - ymax [float] (必需): 矩形上边界纬度

54. 工具名称: forecast_rain_ecmwf_stc
描述: 获取指定时段的ECMWF降雨分区统计信息，包括各子流域累计、平均、最大降雨量
类别: flood_control
参数:
  - st [string] (可选): 开始时间，默认当前时间
  - ed [string] (可选): 结束时间，默认开始时间后24小时

55. 工具名称: forecast_rain_ecmwf_acc
描述: 获取所有格网点指定时段的ECMWF累计降雨，返回经纬度和累计降雨值
类别: flood_control
参数:
  - st [string] (必需): 开始时间
  - ed [string] (必需): 结束时间

56. 工具名称: contour_rain_today
描述: 获取8点以后降雨等值面，返回GeoJSON格式的等值面数据
类别: flood_control
参数:
  - t [string] (可选): 时间，默认当前时间，格式: yyyy-MM-dd HH:mm:ss

57. 工具名称: contour_rain_any
描述: 生成/获取任意时段累计降雨等值面
类别: flood_control
参数:
  - st [string] (必需): 开始时间
  - ed [string] (必需): 结束时间

58. 工具名称: contour_rain_plan
描述: 生成/获取方案累计降雨等值面
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

59. 工具名称: contour_rain_proc
描述: 获取逐小时降雨等值面过程
类别: flood_control
参数:
  - t [string] (可选): 时间，默认当前时间

60. 工具名称: contour_rain_acc
描述: 获取不同时段累计降雨等值面，interval负数表示历史，正数表示未来
类别: flood_control
参数:
  - t [string] (可选): 时间，默认当前时间
  - interval [integer] (必需): 时段间隔(小时)，可选值: -1/-12/-24/-48/-72/1/12/24/48/72

61. 工具名称: contour_rain_future_img
描述: 获取未来24/48/72小时降雨等值面图片(Base64格式)
类别: flood_control
参数:
  - ind [integer] (必需): 时段索引: 0=24小时, 1=48小时, 2=72小时
  - time [string] (可选): 时间，默认当前时间

62. 工具名称: contour_rain_update
描述: 更新等值面(无需登录)
类别: flood_control
参数:
  无参数

63. 工具名称: monitor_rain_area_proc_whole
描述: 获取指定时段的流域整体面雨量过程
类别: flood_control
参数:
  - st [string] (必需): 开始时间
  - ed [string] (必需): 结束时间

64. 工具名称: monitor_rain_manual
描述: 手动更新降水监测数据(无需登录)
类别: flood_control
参数:
  - st [string] (必需): 开始时间
  - ed [string] (必需): 结束时间

65. 工具名称: model_rain_pattern_list
描述: 查询设计雨型列表
类别: flood_control
参数:
  无参数

66. 工具名称: model_rain_pattern_add
描述: 新增设计雨型
类别: flood_control
参数:
  - name [string] (必需): 雨型名称
  - type [string] (可选): 雨型类型: 0=自定义雨型, 1=设计雨型
  - json [string] (必需): 雨型过程JSON

67. 工具名称: model_rain_pattern_detail
描述: 查看设计雨型详情
类别: flood_control
参数:
  - id [integer] (必需): 雨型ID

68. 工具名称: model_typical_rain_list
描述: 分页查询典型暴雨列表
类别: flood_control
参数:
  - id [integer] (可选): 暴雨ID
  - name [string] (可选): 暴雨名称
  - page [integer] (可选): 页码，默认1
  - limit [integer] (可选): 每页条数，默认10

69. 工具名称: model_typical_rain_add
描述: 新增典型暴雨
类别: flood_control
参数:
  - name [string] (必需): 暴雨名称
  - process [array] (必需): 降雨过程数据

70. 工具名称: model_typical_rain_detail
描述: 查看典型暴雨详情
类别: flood_control
参数:
  - id [integer] (必需): 暴雨ID

71. 工具名称: model_typical_rain_add_from_history
描述: 从历史数据新增典型暴雨
类别: flood_control
参数:
  - st [string] (必需): 开始时间
  - ed [string] (必需): 结束时间
  - name [string] (必需): 暴雨名称

72. 工具名称: model_rain_area_get_by_plan
描述: 获取指定方案的各子流域降雨过程(无需登录)，返回按子流域编码分组的降雨时序数据
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

73. 工具名称: model_rain_area_get_basin_area_rain_stc
描述: 获取指定方案的全流域平均面雨量过程及统计值(无需登录)，包括累计、最大降雨量和平均值
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

74. 工具名称: model_rain_area_get_basin_area_rain_acc
描述: 获取指定方案的全流域平均面雨量过程及实时累计降雨
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

75. 工具名称: model_rain_area_get_basin_list
描述: 获取指定方案有降雨预报的流域清单
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

76. 工具名称: model_rain_area_detail
描述: 获取指定方案、指定流域的降雨过程及统计，包括累计、最大降雨量和时间
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码
  - bsn_code [string] (必需): 流域编码

77. 工具名称: model_rain_area_get_by_rsvr
描述: 获取指定方案、指定水文站的上游流域降雨过程
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码
  - stcd [string] (必需): 水文站编码

78. 工具名称: model_rain_area_forecast_rain_stc
描述: 获取自动预报方案的降雨态势，包括平均、最大降雨量和降雨等级
类别: flood_control
参数:
  - interval [integer] (必需): 时段间隔(小时)

79. 工具名称: model_rain_area_add_ecmwf
描述: 根据格网预报(ECMWF)设置方案降雨过程
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

80. 工具名称: model_rain_area_add_ecmwf_translate
描述: 根据格网预报设置方案降雨过程(可放大平移)，支持设置放大倍数和经纬度偏移量
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码
  - factor [float] (可选): 放大倍数，默认1.0
  - dlgtd [float] (可选): 经度偏移量，默认0
  - dlttd [float] (可选): 纬度偏移量，默认0

81. 工具名称: model_rain_area_add_manual
描述: 手动设置方案降雨过程，通过JSON格式指定降水量时序数据
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码
  - bsn_code [string] (可选): 子流域编码(avg表示全流域平均)
  - drp_json [string] (必需): 降水量JSON字符串，格式如：{"2025-12-16 08:00:00":3.68,"2025-12-16 09:00:00":6.2}
  - source [string] (可选): 数据来源: 0=实测, 1=预报, 2=指定, 3=无降雨

82. 工具名称: model_rain_area_add_manual_center
描述: 手动设置方案降雨过程(可设降雨中心)，支持设置多个降雨中心区域
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码
  - centers [array] (必需): 降雨中心列表，每个中心需包含drpJson(降雨过程JSON)和polyWkt(面要素WKT格式)

83. 工具名称: model_rain_area_add_bnd
描述: 从数据库导入方案降雨过程
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

84. 工具名称: flood_damage_loss_calc
描述: 根据模型编码和业务类型计算洪涝灾害造成的损失，包括受灾面积、受灾人口、受灾GDP、受灾企业数等，并返回受灾村庄和区县的GeoJSON数据
类别: damage_assess
参数:
  - code [string] (必需): 模型编码，如 model_20240829111000
  - businessType [string] (必需): 业务类型：flood_dispatch_route_wg-分洪调度路线、flood_dispatch_wg-分洪调度

85. 工具名称: hedge_placement_list
描述: 根据预案编码查询避险安置点列表，包括安置点名称、位置、联系人、容纳人数等信息
类别: damage_assess
参数:
  - planCode [string] (必需): 预案编码，如 model_20250524100026

86. 工具名称: hedge_transfer_route_list
描述: 根据预案编码查询转移路线列表，包括转移村庄、目标安置点、转移时间、联系人等信息
类别: damage_assess
参数:
  - planCode [string] (必需): 预案编码，如 model_20250524100026

87. 工具名称: model_result_outflow_delete
描述: 删除产流结果，根据方案编码和可选的流域编码删除子流域洪水计算结果
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码
  - bsn_code [string] (可选): 流域编码（可选）

88. 工具名称: model_result_outflow_get_basin_list
描述: 获取指定方案的子流域基础信息清单，返回子流域编码和名称列表
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

89. 工具名称: model_result_outflow_detail
描述: 获取指定方案、指定子流域的降雨及洪水过程结果及统计结果，包括降雨过程、洪水过程、峰值时间、累计降雨、洪峰流量等
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码
  - bsn_code [string] (必需): 流域编码

90. 工具名称: model_result_outflow_source
描述: 获取洪水来源类型：0=降雨计算、1=直接导入、2=无洪水
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

91. 工具名称: loss_plan_list
描述: 分页查询淹没分析方案列表，支持按编码、名称、状态、蓄滞洪区编码、类型等条件过滤
类别: flood_control
参数:
  - code [string] (可选): 方案编码（可选）
  - name [string] (可选): 方案名称（可选）
  - status [string] (可选): 计算状态：待计算/计算中/计算成功/计算失败（可选）
  - fsda_code [string] (可选): 蓄滞洪区编码（可选）
  - model_type [string] (可选): 类型：0=蓄滞洪区, 1=滩地（可选）
  - page [integer] (可选): 页码，默认1
  - limit [integer] (可选): 每页条数，默认10

92. 工具名称: loss_plan_add
描述: 新增淹没分析方案，用于创建新的洪水淹没分析计算方案
类别: flood_control
参数:
  - code [string] (必需): 方案编码
  - name [string] (必需): 方案名称
  - descrip [string] (可选): 方案描述（可选）
  - param_json [string] (可选): 参数JSON（可选）
  - fsda_code [string] (可选): 蓄滞洪区编码，可多个（可选）
  - fsda_name [string] (可选): 蓄滞洪区名称，可多个（可选）
  - model_type [string] (可选): 类型：0=蓄滞洪区, 1=滩地（可选）
  - save [string] (可选): 是否保存方案（可选）

93. 工具名称: loss_plan_delete
描述: 删除指定的淹没分析方案
类别: flood_control
参数:
  - code [string] (必需): 方案编码

94. 工具名称: loss_plan_calc
描述: 执行淹没分析方案计算，返回预计计算所需时间（秒）
类别: flood_control
参数:
  - code [string] (必需): 方案编码

95. 工具名称: loss_plan_detail
描述: 获取淹没分析方案详情及计算结果数据
类别: flood_control
参数:
  - code [string] (必需): 方案编码

96. 工具名称: loss_plan_gis
描述: 获取淹没分布GIS数据，返回GeoJSON格式的淹没范围和深度信息
类别: flood_control
参数:
  - path [string] (必需): 结果文件路径

97. 工具名称: loss_plan_auto
描述: 自动计算淹没分析（无需登录）
类别: flood_control
参数:
  无参数

98. 工具名称: flood_plan_list_all
描述: 查询全部防汛预案列表（不分页），支持按预案名称、文号、年度、分类等条件过滤
类别: flood_control
参数:
  - title [string] (可选): 预案名称（可选）
  - code [string] (可选): 预案文号（可选）
  - year [string] (可选): 年度（可选）
  - type1 [string] (可选): 一级分类（可选）
  - type2 [string] (可选): 二级分类（可选）

99. 工具名称: flood_plan_add
描述: 新增防汛预案（支持文件上传），用于创建新的防汛预案记录
类别: flood_control
参数:
  - title [string] (必需): 预案名称
  - code [string] (可选): 预案文号（可选）
  - year [string] (可选): 年度（可选）
  - type1 [string] (可选): 一级分类（可选）
  - type2 [string] (可选): 二级分类（可选）
  - remark [string] (可选): 备注（可选）
  - rela [string] (可选): 关联信息（可选）
  - file_id [string] (可选): 已有文件ID（可选，如不上传新文件可直接指定）

100. 工具名称: flood_plan_delete
描述: 删除指定的防汛预案
类别: flood_control
参数:
  - id [integer] (必需): 预案ID

101. 工具名称: flood_plan_detail
描述: 查看防汛预案详情，包括预案名称、文号、年度、分类、文件信息等
类别: flood_control
参数:
  - id [integer] (必需): 预案ID

102. 工具名称: flood_plan_catalog
描述: 获取防汛预案类型目录，返回一级分类及其下属二级分类的树形结构
类别: flood_control
参数:
  无参数

103. 工具名称: monitor_rsvr_now
描述: 获取水库河道实时水情（无需登录），返回水位、库容、入库流量、出库流量等实时数据
类别: flood_control
参数:
  无参数

104. 工具名称: monitor_rsvr_stc
描述: 获取水库当前形势统计，返回总数、正常数、预警数、危险数等统计信息
类别: flood_control
参数:
  无参数

105. 工具名称: monitor_rsvr_track
描述: 水雨情态势过程回溯，获取指定时段内水库水情变化过程
类别: flood_control
参数:
  - st [string] (必需): 开始时间，格式: yyyy-MM-dd HH:mm:ss
  - ed [string] (必需): 结束时间，格式: yyyy-MM-dd HH:mm:ss

106. 工具名称: monitor_rsvr_storage
描述: 水库纳蓄能力分析，返回总库容、当前蓄量、可用库容、蓄水率等信息
类别: flood_control
参数:
  - goal [integer] (必需): 目标水位或库容指标

107. 工具名称: mike_gate_all
描述: 获取闸门工情（无需登录），返回闸门状态（全开/半开/全关）、开度、开启孔数等信息
类别: flood_control
参数:
  无参数

108. 工具名称: mike_runoff
描述: 获取子流域NAM模型产流结果（无需登录），返回各子流域的产流时间序列
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

109. 工具名称: mike_rsvr_info
描述: 获取水库基本信息（无需登录），包括水库编码、名称、汛限水位、正常水位、死水位、总库容等
类别: flood_control
参数:
  - model_instance [string] (可选): 模型实例编码（可选）

110. 工具名称: mike_control
描述: 获取水库的可控建筑物，返回泄洪洞、溢洪道等可控设施信息及最大过流能力
类别: flood_control
参数:
  - stcd [string] (必需): 水库编码

111. 工具名称: mike_hvrela
描述: 获取蓄滞洪区的库容曲线，返回水位-库容关系数据
类别: flood_control
参数:
  - code [string] (必需): 蓄滞洪区编码

112. 工具名称: mike_spec_time
描述: 获取指定时刻的水情，返回各水库测站的水位、入库流量、出库流量等数据
类别: flood_control
参数:
  - time [string] (可选): 指定时间，格式: yyyy-MM-dd HH:mm:ss（可选，默认当前时间）

113. 工具名称: mike_cal_pa
描述: 计算指定时间各子流域的前期影响雨量(Pa值)，用于洪水预报模型参数计算
类别: flood_control
参数:
  - time [string] (可选): 指定时间，格式: yyyy-MM-dd HH:mm:ss（可选，默认当前时间）

114. 工具名称: mike_fsda_struct
描述: 获取指定业务模型对应蓄滞洪区的建筑物信息，如分洪堰等
类别: flood_control
参数:
  - business_code [string] (必需): 业务模型编码

115. 工具名称: mike_fsda_set_boundary
描述: 设置蓄滞洪区进洪预演模型的边界条件，用于配置模型计算参数
类别: flood_control
参数:
  - boundary_config [object] (必需): 边界条件配置JSON对象，根据具体蓄滞洪区模型定义

116. 工具名称: auto_forcast
描述: 创建洪水自动预报模型方案并进行计算
类别: hydro_model
参数:
  无参数

117. 工具名称: create_model
描述: 手工创建模型方案，仅创建方案不设置边界条件，也不计算
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID，如'model_20230513101926'
  - fangan_name [string] (必需): 方案名称
  - start_timestr [string] (必需): 开始时间，格式如'2021/07/20 00:00:00'
  - end_timestr [string] (必需): 结束时间，格式如'2021/07/21 00:00:00'
  - fangan_desc [string] (必需): 方案描述，如'1日模拟'
  - step_saveminutes [integer] (必需): 结果保存步长(分钟)
  - base_plan_code [string] (可选): 基础方案ID，默认采用空字符串

118. 工具名称: change_model_baseinfo
描述: 修改模型方案名称、描述和保存时间步长
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - fangan_name [string] (必需): 新的模型名称
  - model_desc [string] (必需): 新的模型描述
  - step_save_minutes [integer] (必需): 保存时间步长(分钟)

119. 工具名称: del_model
描述: 删除模型方案，返回剩下的模型方案基础信息集合
类别: hydro_model
参数:
  - plan_code [string] (必需): 要删除的方案ID

120. 工具名称: run_model
描述: 计算模型，返回所需的计算时间(秒)
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID

121. 工具名称: run_model_quick
描述: 一维快速计算模型(不进行GIS结果后处理)，返回所需的计算时间(秒)
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID

122. 工具名称: stop_model
描述: 停止模型计算，返回成功信息
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID

123. 工具名称: modify_initial
描述: 修改方案的水库河道初始水位条件
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - initial_level [string] (必需): 初始水位设置。可输入'monitor'(采用监测水位)，或水位字典JSON格式如'{"站点ID1": 水位值1, "站点ID2": 水位值2}'

124. 工具名称: change_rfmodel
描述: 修改方案的各个子流域产汇流模型类型
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - rf_model [string] (可选): 产汇流模型参数JSON，格式为'{"子流域编码1": "模型编码1", "子流域编码2": "模型编码2"}'。模型编码共3种: 'nam'、'swmm5'、'xaj'。可为空对象或空字符串

125. 工具名称: change_boundry
描述: 修改方案的洪水入流边界条件，可指定为利用降雨计算洪水、直接指定子流域洪水过程、指定河道洪水过程或无洪水入流
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - bnd_type [string] (必需): 边界类型: 'rf_model'(降雨计算洪水), 'reach_inflow'(指定河道洪水), 'no_inflow'(无洪水入流), 'catchment_inflow'(指定子流域洪水)
  - bnd_value [string] (可选): 边界值JSON。当bnd_type为'reach_inflow'时，格式为'{"边界条件编码1": {"时间1": 流量1, "时间2": 流量2}}'；当bnd_type为'catchment_inflow'时，格式为'{"子流域编码1": {"时间1": 流量1}}'。其他类型不需要此参数

126. 工具名称: modify_gatestate
描述: 修改方案闸站调度设置
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - gate_dispatch [string] (必需): 调度方式。可为'monitor'(采用当前监测的闸站状态工情)、'gaterule'(采用各闸站设计调度规则)、或调度指令数组JSON格式'[["建筑物编码1",["时间1","操作类型1","闸孔数","值"]],...]'

127. 工具名称: change_reach_break
描述: 修改方案河堤溃口设置
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - break_name [string] (必需): 溃口名称
  - location [array] (必需): 溃口位置坐标 [经度, 纬度]
  - fh_width [float] (必需): 溃口宽度(米)
  - fh_minutes [integer] (必需): 溃堤时长(分钟)
  - break_condition [string] (必需): 溃决时机描述: 'max_level'(河道水位达到最高水位) 或 'set_level'(指定河道水位)
  - break_level [float] (必需): 溃决水位。当break_condition为'max_level'时可填任意值(如0)，否则填指定值

128. 工具名称: set_dispatch_target
描述: 设置方案的优化调度目标参数
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - dd_target [object] (必需): 调度目标对象，格式为'{"name": "元村", "stcd": "31004300", "max_discharge": 2500}'，包含水文站名称、水文站ID、最大允许洪峰流量
  - res_level_constraint [array] (必需): 水库调洪水位约束数组，格式为'[{"name": "双泉水库", "stcd": "31006950", "level_name": "防洪高水位", "level_value": 142.3}]'
  - other_constraint [object] (必需): 其他约束对象，格式为'{"gate": true, "reach": true, "xzhq_level": true}'，分别为闸门过流能力约束、河道过流能力约束、滞洪区滞洪水位约束

129. 工具名称: iter_cal
描述: 开始方案的优化迭代计算
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID

130. 工具名称: backcal_resdd
描述: 反向推演水库的调度方案和该调度方案下的调蓄结果。需要设置水库允许达到的最高水位，并且只针对已经完成的预报预演方案
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - res_name [string] (必需): 水库名称
  - max_level [float] (必需): 允许最高水位

131. 工具名称: set_fault_gate
描述: 设置方案的故障闸门
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - sluice_code [string] (必需): 故障水闸编码，如'QHNZ_XHKJZZ'
  - fault_desc [string] (必需): 故障信息描述，如'部分闸门无法完全关闭'
  - fault_gate_codes [array] (必需): 故障闸门编码数组，如['XHK_JZZ2', 'XHK_JZZ4']
  - gate_openings [array] (必需): 水闸各闸门开度数组，如[0, 0.5, 0, 0.2, 0]

132. 工具名称: get_sampleline
描述: 获取GIS样板线，为geojson格式的河道分段线要素，用于在地图区分色动态渲染过程结果，如流量、流速等
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

133. 工具名称: get_reachinfo
描述: 获取河道基本信息，包括河道名称、编码、起止桩号及长度等信息
类别: hydro_model
参数:
  - model_instance [string] (必需): 模型实例名称字符串

134. 工具名称: get_gatestate
描述: 获取全流域里各闸站建筑最新状态监测信息，包括闸门状态、开孔数、开度、更新时间
类别: hydro_model
参数:
  - business_code [string] (必需): 业务编码字符串

135. 工具名称: get_sectiondata
描述: 根据断面STCD和桩号，获取河道断面原始测量数据。当断面为水文站点或闸站时，第1个参数为该站点STCD，第2个为空字符串；否则第1个参数为河道编码，第2个为桩号
类别: hydro_model
参数:
  - stcd_or_reach_code [string] (必需): 站点STCD(如'31004300')或河道编码(如'GQ')
  - chainage [string] (必需): 桩号。当第1个参数为站点STCD时，填空字符串''；否则填具体桩号值(如'155000')

136. 工具名称: get_sectiondata_frompoint
描述: 根据坐标点，获取河道断面原始测量数据
类别: hydro_model
参数:
  - longitude [string] (必需): 经度，如'114.15169'
  - latitude [string] (必需): 纬度，如'35.483368'

137. 工具名称: get_reachsection_location
描述: 根据河道断面桩号，获取该河道断面中心点的经纬度坐标位置信息
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - section_location [array] (必需): 断面位置信息数组，格式如[["GQ",53263],["GQ",43263],["WH",13263]]，包含河道编码和桩号

138. 工具名称: get_station_info
描述: 获取河道上各大中型水库、河道水文站点、河道控制闸站的基本信息和监测水情信息，包括站点stcd、所在河道和桩号、控制流域面积、水位流量等监测水情信息等
类别: hydro_model
参数:
  无参数

139. 工具名称: get_strddrule_info
描述: 获取水库、河道闸站等所有洪水控制建筑的规则调度信息
类别: hydro_model
参数:
  - business_code [string] (必需): 业务编码字符串

140. 工具名称: get_control_strs
描述: 根据业务编码和站点STCD获取关联的洪水控制建筑物，如水库的各个溢流堰和泄洪洞，蓄滞洪区的各个进洪分洪闸堰
类别: hydro_model
参数:
  - business_code [string] (必需): 业务编码
  - obj_stcd [string] (必需): 对象站点编码

141. 工具名称: get_now_waterinfo
描述: 获取所有水库、河道闸站、水文站点当前最新水情信息。如果业务编码字符串为空字符串，则获取所有水库闸站和水文站点的当前水情，否则是业务模型相关的
类别: hydro_model
参数:
  - business_code [string] (可选): 业务编码字符串，可为空字符串

142. 工具名称: get_design_flood
描述: 获取和业务模型相关的各河道不同量级设计洪水过程，如50年一遇设计洪水过程
类别: hydro_model
参数:
  - business_code [string] (必需): 业务编码字符串

143. 工具名称: get_nsbd_sectioninfo
描述: 获取流域范围内，各河道与南水北调交叉断面的基本信息，包括交叉断面位置、设计水位、设计流量、校核流量、堤顶高程等
类别: hydro_model
参数:
  无参数

144. 工具名称: get_business_view
描述: 获取业务模型的默认初始三维场景相机姿态信息，包括相机位置坐标、朝向和俯仰角
类别: hydro_model
参数:
  - business_model [string] (必需): 业务模型字符串

145. 工具名称: get_rfmodel
描述: 获取方案的产汇流模型类型，返回各子流域采用的产汇流模型编码（共3种：nam、swmm5、xaj）
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

146. 工具名称: get_reach_break
描述: 获取方案河堤溃口设置信息，包括溃口编码、名称、位置、溃口宽度、溃堤时长、溃决水位、溃口底高程、开始溃口时间等
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

147. 工具名称: get_faultgate_baseinfo
描述: 获取故障水闸的闸门基本信息，根据业务编码获取，一个业务编码对应一个故障水闸。返回建筑物编码、名称及各闸门的编码、名称、闸底高程、闸门高度、经纬度坐标等信息
类别: hydro_model
参数:
  - business_code [string] (必需): 业务编码字符串

148. 工具名称: get_fault_gate
描述: 获取方案的故障闸门信息，包括故障水闸名称、故障描述、各闸门最大开度和当前开度、故障闸门名称及经纬度
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

149. 工具名称: get_ddinfo
描述: 获取模型方案所有可控建筑物的调度信息，包括建筑物编码、序号、名称、类型、所在河道及闸门调度过程
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

150. 工具名称: get_initial_waterlevel
描述: 获取模型方案的初始水情信息，包括各水库和河道站点的序号、名称、初始水位、水位来源、stcd编码等
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

151. 工具名称: get_bndinfo
描述: 获取模型方案的边界条件信息，包括边界条件类型描述（如'降雨计算洪水'）和边界条件值（各子流域的流量过程）
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

152. 工具名称: get_dispatch_target
描述: 获取方案的优化调度目标设置信息，包括方案ID、调度目标（站点名称、stcd、最大流量）、各水库约束水位及其他约束条件
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

153. 工具名称: get_models
描述: 获取已有所有模型方案信息，包括方案名称、描述、业务模型编码、起止时间、状态、进度等12个属性
类别: hydro_model
参数:
  - model_instance [string] (可选): 模型实例名称字符串，默认为'wg_mike11'

154. 工具名称: get_dispatch_plan
描述: 获取方案主要控制闸站的简短调度指令，包含水库、河道闸站、蓄滞洪区3种类型的各控制闸站的调度信息
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

155. 工具名称: get_tjdata_result
描述: 获取方案的结果数据，包含水库、河道断面、蓄滞洪区的洪水计算结果以及结果概述、河道风险，此外还可能包含调度方案结果
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

156. 工具名称: get_gisgc_polygon_result
描述: 获取方案某时刻河道水面GIS面要素结果，为geojson格式的带Z值的三维水面要素，用于在三维场景中绘制三维水面
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - now_time [string] (必需): 时间字符串，如'2021/07/20 08:00:00'

157. 工具名称: get_sampleline_data_result
描述: 获取方案的GIS过程线的全过程属性结果，用于在地图区分色动态渲染过程结果，如流量、流速等
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - gis_restype [string] (必需): 结果数据类型: 'Waterlevel'(水位), 'Speed'(流速), 'Waterh'(水深), 'Discharge'(流量)

158. 工具名称: get_gistj_result
描述: 获取方案的GIS统计线结果，为geojson格式的河道分段线要素，用于在地图区分色渲染全过程最大流量、流速等分布结果
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

159. 工具名称: get_gistj_polygon_result
描述: 获取方案的GIS统计面结果(淹没面)，为geojson格式的二维面要素，用于在地图中分水渲染淹没区水深分布
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

160. 工具名称: get_point_result
描述: 查询方案河道上某点的水位流量等结果，用于在地图中点击查询某位置结果信息。如果时间为空字符串，则返回时间序列
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - now_time [string] (必需): 时间字符串，如'2021/07/20 08:00:00'。如果为空字符串''，则返回时间序列
  - jd [string] (必需): 经度
  - wd [string] (必需): 纬度

161. 工具名称: get_zp_result
描述: 获取方案某类结果的顺河道纵剖面数据，用于前端页面纵剖图绘制
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - res_type [string] (必需): 结果数据类型: 'swzd_result'(水位纵断), 'qzd_result'(流量纵断), 'vzd_result'(流速纵断)

162. 工具名称: get_reachsections
描述: 获取方案有水位结果的河道断面桩号清单，包括各河道基本信息和各河道有水位结果的断面桩号
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

163. 工具名称: get_sectionres
描述: 获取方案单一河道断面的水位流量过程
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - reach_name [string] (必需): 河道名称(编码)
  - chainage [number] (必需): 断面桩号

164. 工具名称: get_sectionlist_res
描述: 获取方案多个河道断面的水位流量过程
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - sections [array] (必需): 断面数组，格式为[{'reach':'河道编码1','chainages':[桩号1,桩号2]},{'reach':'河道编码2','chainages':[桩号1]}]

165. 工具名称: get_catchment_discharges
描述: 获取方案多个子流域的产汇流模型流量过程
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - sub_catchment_q [object] (必需): 子流域属性对象，属性和值均为子流域编码，如{'jyh_czyx':'jyh_czyx','jlh_jgsk':'jlh_jgsk'}

166. 工具名称: get_gateres
描述: 获取方案某闸门的水力要素结果，包括过闸流量、上下游水位过程、流速过程、水头差等
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - gate_name [string] (必需): 闸门编码

167. 工具名称: get_atreach
描述: 根据方案ID获取该方案的特殊河道断面信息，包括河道ID和桩号
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

168. 工具名称: get_risk_warning
描述: 获取方案的风险预警信息，包含水库风险预警、河道风险预警、蓄滞洪区进洪风险预警、降雨预警、南水北调交叉断面风险预警、山洪风险预警
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

169. 工具名称: get_history_autoforcast_list
描述: 获取历史洪水自动预报方案信息清单，包含方案ID、预报起止时间和本场次降雨总降雨量
类别: hydro_model
参数:
  无参数

170. 工具名称: del_history_autoforcast
描述: 删除某场历史自动预报方案
类别: hydro_model
参数:
  - history_plan_id [string] (必需): 历史预报方案ID字符串

171. 工具名称: get_rain_flood_list
描述: 获取预演场次洪水信息列表，所有预演方案均关联有一场场次洪水，一场场次洪水可能对应多个预演方案，但只有一个推荐方案
类别: hydro_model
参数:
  无参数

172. 工具名称: get_rainflood_plan_list
描述: 获取某场次洪水的预演方案清单，包含方案名称、描述、业务模型、起止时间、状态等信息
类别: hydro_model
参数:
  - flood_id [string] (必需): 场次洪水ID字符串

173. 工具名称: change_rainflood_recomplan
描述: 修改某场次洪水的推荐预演方案
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

174. 工具名称: important_inspect
描述: 获取预演方案的工程重点巡查区域信息，即通过方案预演后得到的工程风险区域作为重点巡查区域，包含水库、河道、蓄滞洪区的巡查信息
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

175. 工具名称: get_history_autoforcast_res
描述: 获取历史洪水自动预报结果，结果与get_tjdata_result接口返回结果相同
类别: hydro_model
参数:
  - history_plan_id [string] (必需): 历史预报ID字符串

176. 工具名称: get_mountain_forecast_flood
描述: 获取山区预报信息，包括山洪区域名称、村庄名称、经纬度、被淹时间、风险等级等
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串


## 可用工作流

1. flood_forecast_workflow - 洪水预报工作流
   触发条件: 用户询问洪水预报相关问题
   
2. flood_simulation_workflow - 洪水预演工作流
   触发条件: 用户要求进行洪水模拟

3. emergency_plan_workflow - 应急预案工作流
   触发条件: 用户需要生成防洪预案

4. latest_flood_forecast_query - 最新洪水预报结果查询
   触发条件: 用户询问最新预报结果


## 相关知识和业务流程参考
以下是相关的知识库内容：

[1] (监测设施)
水文监测站网是水文信息采集的基础设施，包括：
                - 水位站：监测河道、水库水位变化
                - 雨量站：监测降雨量和降雨强度
                - 流量站：监测河道流量
                - 水质站：监测水体水质指标
                卫共流域共有各类水文监测站点约200个，实现了重点区域全覆盖。

[2] (专业知识)
洪水预报是根据实测和预报的水文气象资料，应用水文学方法，
                对未来一定时期内的洪水过程进行预测。主要方法包括：
                1. 降雨径流预报：根据降雨量预测径流量
                2. 河道洪水演进：利用马斯京根法等计算洪水传播
                3. 水库调度：考虑水库调蓄作用优化泄洪方案
                预报精度受数据质量、模型参数等因素影响。

[3] (防洪知识)
防洪预警等级分为四级：
                - 蓝色预警（IV级）：可能发生一般洪水
                - 黄色预警（III级）：可能发生较大洪水
                - 橙色预警（II级）：可能发生大洪水
                - 红色预警（I级）：可能发生特大洪水
                各级预警对应不同的应急响应措施和人员转移要求。


## 用户意图
意图类别: data_query
提取实体: {'locations': ['盘石头水库', '小南海水库'], 'data_type': '水位', 'time': '当前'}

## 用户消息
盘石头水库和小南海水库相比，哪个当前水位高？

## 输出要求
请生成执行计划，返回JSON格式:
{
    "steps": [
        {
            "step_id": 1,
            "description": "步骤描述",
            "tool_name": "工具名称（如果需要）",
            "tool_args": {"参数": "值"},
            "dependencies": [],
            "is_async": false
        }
    ],
    "estimated_time_seconds": 30,
    "output_type": "text 或 web_page"
}

规划原则:
1. 步骤应该清晰、可执行
2. 正确设置步骤间的依赖关系
3. 耗时操作（如模型调用）应标记为异步
4. 最后一步不需要指定工具，系统会自动生成响应
5. 只使用可用工具列表中存在的工具名称，不要使用不存在的工具如"generate_response"
6. 参考"相关知识和业务流程参考"中的信息，优化执行计划的步骤和工具选择

```

**LLM响应**:
```
{'steps': [{'step_id': 1, 'description': '登录卫共流域数字孪生系统以获取访问令牌', 'tool_name': 'login_basin_system', 'tool_args': {}, 'dependencies': [], 'is_async': False}, {'step_id': 2, 'description': '查询盘石头水库的测站编码(stcd)', 'tool_name': 'get_map_data', 'tool_args': {'ref_table': 'geo_res_base', 'filter_field': 'res_name', 'filter_operator': '=', 'filter_value': '盘石头水库'}, 'dependencies': [1], 'is_async': False}, {'step_id': 3, 'description': '查询小南海水库的测站编码(stcd)', 'tool_name': 'get_map_data', 'tool_args': {'ref_table': 'geo_res_base', 'filter_field': 'res_name', 'filter_operator': '=', 'filter_value': '小南海水库'}, 'dependencies': [1], 'is_async': False}, {'step_id': 4, 'description': '获取盘石头水库的最新实时水位数据', 'tool_name': 'query_reservoir_last', 'tool_args': {'stcd': '$$STEP_2[0].stcd$$'}, 'dependencies': [2], 'is_async': False}, {'step_id': 5, 'description': '获取小南海水库的最新实时水位数据', 'tool_name': 'query_reservoir_last', 'tool_args': {'stcd': '$$STEP_3[0].stcd$$'}, 'dependencies': [3], 'is_async': False}, {'step_id': ...(已截断)
```

## 任务执行(LLM) (Executor._execute_with_llm)
**时间**: 2025-12-26 11:37:51
**提示词模板**: EXECUTOR_LLM_PROMPT

**上下文变量**:
- task_description: 对比两个水库的当前水位并回答用户问题
- user_message: 盘石头水库和小南海水库相比，哪个当前水位高？
- execution_results: 步骤1 (成功): {'success': True, 'data': {'token': 'eyJhbGciOiJIUzUxMiJ9.eyJ1c2VySWQiOjEzMzk1NTA0Njc5Mzk2MzkyOTksImFjY291bnQiOiJhZG1pbiIsInV1aWQiOiJmMmZjNjUwMC1kOWU4LTQ3MGEtYjRjNS1hODhhNDE3M2U3ZDgiLCJyZW1lbWJlck1lIjpmYWxzZSwiZXhwaXJhdGlvbkRhdGUiOjE3NjczMjUwOTI2MjksImNhVG9rZW4iOm51bGwsIm90aGVycyI6bnVsbCwic3ViIjoiMTMzOTU1MDQ2NzkzOTYzOTI5OSIsImlhdCI6MTc2NjcyMDI5MiwiZXhwIjoxNzY3MzI1MDkyfQ.C7j4yyDQ5dEceShpRQNDcICdsuEcX-VeVVmZXjsAElPhAMiQGB3yFWur174XxprDBmCVJmhAvGTTdQS4WpGAyQ', 'userId': '13395504679396392...(已截断)
- retrieved_documents: 无

**完整提示词**:
```
你是卫共流域数字孪生系统的智能助手。

## 任务
对比两个水库的当前水位并回答用户问题

## 用户原始消息
盘石头水库和小南海水库相比，哪个当前水位高？

## 已有执行结果
步骤1 (成功): {'success': True, 'data': {'token': 'eyJhbGciOiJIUzUxMiJ9.eyJ1c2VySWQiOjEzMzk1NTA0Njc5Mzk2MzkyOTksImFjY291bnQiOiJhZG1pbiIsInV1aWQiOiJmMmZjNjUwMC1kOWU4LTQ3MGEtYjRjNS1hODhhNDE3M2U3ZDgiLCJyZW1lbWJlck1lIjpmYWxzZSwiZXhwaXJhdGlvbkRhdGUiOjE3NjczMjUwOTI2MjksImNhVG9rZW4iOm51bGwsIm90aGVycyI6bnVsbCwic3ViIjoiMTMzOTU1MDQ2NzkzOTYzOTI5OSIsImlhdCI6MTc2NjcyMDI5MiwiZXhwIjoxNzY3MzI1MDkyfQ.C7j4yyDQ5dEceShpRQNDcICdsuEcX-VeVVmZXjsAElPhAMiQGB3yFWur174XxprDBmCVJmhAvGTTdQS4WpGAyQ', 'userId': '1339550467939639299', 'mess步骤2 (成功): {'success': True, 'data': [{'county': '淇滨区', 'dead_cap': '2250', 'res_name': '盘石头水库', 'che_flo_sta': '0.05', 'che_flo_lev': '275', 'main_dam_wav_wal_elev': '276.9', 'main_dam_top_len': '606', 'wat_shed_area': 1915.0, 'id': '298ab3d2-b828-4f6c-8bf3-9198b57a4baa', 'norm_pool_stag_cap': '30275', 'longitude': 114.053761, 'tot_cap': '60800', 'ben_res_cap': '28750', 'daad_mul_aver_ruof': '36000', 'che_flo_flow': '15400', 'town': '大河涧乡', 'shape': 'POINT (114.053761714 35.8415127740001)', 'res_type': '1步骤3 (成功): {'success': True, 'data': [{'county': '龙安区', 'dead_cap': '460', 'res_name': '小南海水库', 'che_flo_sta': '0.05', 'che_flo_lev': '187.8', 'main_dam_wav_wal_elev': '189.2', 'main_dam_top_len': '394.5', 'wat_shed_area': 850.0, 'id': '7e34ee7b-f609-4617-ac3e-4db20193d88d', 'norm_pool_stag_cap': '4800', 'longitude': 114.097438, 'tot_cap': '10750', 'ben_res_cap': '4363', 'daad_mul_aver_ruof': '4840', 'che_flo_flow': '8440', 'town': '善应镇', 'shape': 'POINT (114.097438574 36.033506038)', 'res_type': '1', 'sw_步骤4 (成功): {'success': True, 'data': [{'sort': None, 'lgtd': 114.1281, 'lttd': 35.83131, 'stnm': '盘石头', 'warn': None, 'stazt': None, 'rvnm': '淇河', 'hnnm': '漳卫南运河', 'bsnm': '海河', 'stlc': '豫-淇县', 'addvcd': '410622', 'sttp': 'RR', 'tm': '2025-12-26 08:00:00', 'stcd': '31005650', 'rz': 245.08, 'w': 212.74, 'otq': 6.56, 'rwptn': '6', 'inq': 6.56, 'rwchrcd': None, 'inqdr': 24.0, 'msqmt': None, 'blrz': None}], 'error': None, 'execution_time_ms': 39, 'metadata': {'query_type': 'reservoir_last', 'record_count': 1}}步骤5 (成功): {'success': True, 'data': [{'sort': None, 'lgtd': 114.1, 'lttd': 36.033055, 'stnm': '小南海', 'warn': None, 'stazt': None, 'rvnm': '安阳河', 'hnnm': '漳卫南运河', 'bsnm': '海河', 'stlc': '安阳市安阳县善应镇小南海水库管理所', 'addvcd': '410522', 'sttp': 'RR', 'tm': '2025-12-26 08:00:00', 'stcd': '31006700', 'rz': 164.39, 'w': 20.08, 'otq': None, 'rwptn': '6', 'inq': None, 'rwchrcd': None, 'inqdr': None, 'msqmt': None, 'blrz': None}], 'error': None, 'execution_time_ms': 33, 'metadata': {'query_type': 'reservoir_last', 'record_

## 检索到的知识
无

请根据以上信息完成任务，给出清晰、准确的回答。

```

**LLM响应**:
```
根据卫共流域数字孪生系统的最新监测数据（截至2025年12月26日 08:00），盘石头水库和小南海水库的水位对比情况如下：

*   **盘石头水库**：当前水位为 **245.08米**。
*   **小南海水库**：当前水位为 **164.39米**。

**结论：**
**盘石头水库**的当前水位更高，比小南海水库高出 **80.69米**。
```

## Web页面响应合成 (Controller._generate_web_page_response)
**时间**: 2025-12-26 11:37:55
**提示词模板**: RESPONSE_GENERATION_PROMPT

**上下文变量**:
- user_message: 盘石头水库和小南海水库相比，哪个当前水位高？
- intent: data_query
- plan_summary: 1. 登录卫共流域数字孪生系统以获取访问令牌 [completed]
2. 查询盘石头水库的测站编码(stcd) [completed]
3. 查询小南海水库的测站编码(stcd) [completed]
4. 获取盘石头水库的最新实时水位数据 [completed]
5. 获取小南海水库的最新实时水位数据 [completed]
6. 对比两个水库的当前水位并回答用户问题 [completed]
- execution_results: 步骤1:   - success: True
  - data: {'token': 'eyJhbGciOiJIUzUxMiJ9.eyJ1c2VySWQiOjEzMzk1NTA0Njc5Mzk2MzkyOTksImFjY291bnQiOiJhZG1pbiIsInV1aWQiOiJmMmZjNjUwMC1kOWU4LTQ3MGEtYjRjNS1hODhhNDE3M2U3ZDgiLCJyZW1lbWJlck1lIjpmYWxzZSwiZXhwaXJhdGlvbkRhdGUiOjE3NjczMjUwOTI2MjksImNhVG9rZW4iOm51bGwsIm90aGVycyI6bnVsbCwic3ViIjoiMTMzOTU1MDQ2NzkzOTYzOTI5OSIsImlhdCI6MTc2NjcyMDI5MiwiZXhwIjoxNzY3MzI1MDkyfQ.C7j4yyDQ5dEceShpRQNDcICdsuEcX-VeVVmZXjsAElPhAMiQGB3yFWur174XxprDBmCVJmhAvGTTdQS4WpGAyQ', 'userId': '1339550467939639299'...(已截断)
- retrieved_documents: 无相关知识

**完整提示词**:
```
你是卫共流域数字孪生系统的智能助手，负责生成最终响应。

## 用户原始问题
盘石头水库和小南海水库相比，哪个当前水位高？

## 用户意图
data_query

## 执行计划
1. 登录卫共流域数字孪生系统以获取访问令牌 [completed]
2. 查询盘石头水库的测站编码(stcd) [completed]
3. 查询小南海水库的测站编码(stcd) [completed]
4. 获取盘石头水库的最新实时水位数据 [completed]
5. 获取小南海水库的最新实时水位数据 [completed]
6. 对比两个水库的当前水位并回答用户问题 [completed]

## 执行结果
步骤1:   - success: True
  - data: {'token': 'eyJhbGciOiJIUzUxMiJ9.eyJ1c2VySWQiOjEzMzk1NTA0Njc5Mzk2MzkyOTksImFjY291bnQiOiJhZG1pbiIsInV1aWQiOiJmMmZjNjUwMC1kOWU4LTQ3MGEtYjRjNS1hODhhNDE3M2U3ZDgiLCJyZW1lbWJlck1lIjpmYWxzZSwiZXhwaXJhdGlvbkRhdGUiOjE3NjczMjUwOTI2MjksImNhVG9rZW4iOm51bGwsIm90aGVycyI6bnVsbCwic3ViIjoiMTMzOTU1MDQ2NzkzOTYzOTI5OSIsImlhdCI6MTc2NjcyMDI5MiwiZXhwIjoxNzY3MzI1MDkyfQ.C7j4yyDQ5dEceShpRQNDcICdsuEcX-VeVVmZXjsAElPhAMiQGB3yFWur174XxprDBmCVJmhAvGTTdQS4WpGAyQ', 'userId': '1339550467939639299', 'message': '登录成功'}
  - error: None
  - execution_time_ms: 1766
  - metadata: {'code': '00000', 'message': '请求成功'}

步骤2:   - success: True
  - data: [{'county': '淇滨区', 'dead_cap': '2250', 'res_name': '盘石头水库', 'che_flo_sta': '0.05', 'che_flo_lev': '275', 'main_dam_wav_wal_elev': '276.9', 'main_dam_top_len': '606', 'wat_shed_area': 1915.0, 'id': '298ab3d2-b828-4f6c-8bf3-9198b57a4baa', 'norm_pool_stag_cap': '30275', 'longitude': 114.053761, 'tot_cap': '60800', 'ben_res_cap': '28750', 'daad_mul_aver_ruof': '36000', 'che_flo_flow': '15400', 'town': '大河涧乡', 'shape': 'POINT (114.053761714 35.8415127740001)', 'res_type': '1', 'sw_che_fl_flow': '2374', 'fl_low_lim_lev': '248', 'stcd': '31005650', 'des_flo_cri': '1', 'dead_lev': '207', 'upp_lev_flco': '270', 'res_loc': '河南省鹤壁市淇滨区大河涧乡', 'sw_patt': '正槽式溢洪道', 'code': 'HP0014106110000076', 'norm_wat_lev': '254', 'city': '鹤壁市', 'latitude': 35.841512, 'sw_weir_top_wid': '48', 'main_dam_top_elev': '275.7', 'eng_scal': '2', 'coll_date': '2', 'main_dam_top_wid': '8', 'flco_cap': '27560', 'loc_rv_cd': 'FFFAB1A0000L', 'start_date': '1998-10-01', 'stor_fl_cap': '36300', 'norm_pool_stag_area': '13', 'sw_hs_mode': '无控制', 'main_dam_max_heig': '102.2', 'eng_stat': '1', 'sw_weir_top_elev': '254', 'fl_low_lim_lev_cap': '24500', 'sw_nm': '正常溢洪道', 'des_flo_lev': '270.7', 'comp_date': '2007-01-01', 'adm_dep': '9', 'sw_des_fl_flow': '1', 'eng_grad': '2', 'des_flo_flow': '6900', 'loc_rv_nm': '淇河'}]
  - error: None
  - execution_time_ms: 38
  - metadata: {'code': '00000', 'message': '请求成功'}

步骤3:   - success: True
  - data: [{'county': '龙安区', 'dead_cap': '460', 'res_name': '小南海水库', 'che_flo_sta': '0.05', 'che_flo_lev': '187.8', 'main_dam_wav_wal_elev': '189.2', 'main_dam_top_len': '394.5', 'wat_shed_area': 850.0, 'id': '7e34ee7b-f609-4617-ac3e-4db20193d88d', 'norm_pool_stag_cap': '4800', 'longitude': 114.097438, 'tot_cap': '10750', 'ben_res_cap': '4363', 'daad_mul_aver_ruof': '4840', 'che_flo_flow': '8440', 'town': '善应镇', 'shape': 'POINT (114.097438574 36.033506038)', 'res_type': '1', 'sw_che_fl_flow': '7235', 'fl_low_lim_lev': '173.04', 'stcd': '31006700', 'des_flo_cri': '1', 'dead_lev': '150', 'upp_lev_flco': '177', 'res_loc': '河南省安阳市龙安区善应镇', 'sw_patt': '正槽式溢洪道', 'code': 'HP0014105220000223', 'norm_wat_lev': '173', 'city': '安阳市', 'latitude': 36.033506, 'sw_weir_top_wid': '40', 'main_dam_top_elev': '188.1', 'eng_scal': '2', 'coll_date': '2', 'main_dam_top_wid': '7', 'flco_cap': '2411', 'loc_rv_cd': '', 'start_date': '1958-09-01', 'stor_fl_cap': '5911', 'norm_pool_stag_area': '3.16', 'sw_hs_mode': '卷扬式', 'main_dam_max_heig': '54', 'eng_stat': '2', 'sw_weir_top_elev': '168', 'fl_low_lim_lev_cap': '1700', 'sw_nm': '正常溢洪道', 'des_flo_lev': '179.88', 'comp_date': '1964-12-01', 'adm_dep': '1', 'sw_des_fl_flow': '3252', 'eng_grad': '2', 'des_flo_flow': '4300', 'loc_rv_nm': '安阳河'}]
  - error: None
  - execution_time_ms: 35
  - metadata: {'code': '00000', 'message': '请求成功'}

步骤4:   - success: True
  - data: [{'sort': None, 'lgtd': 114.1281, 'lttd': 35.83131, 'stnm': '盘石头', 'warn': None, 'stazt': None, 'rvnm': '淇河', 'hnnm': '漳卫南运河', 'bsnm': '海河', 'stlc': '豫-淇县', 'addvcd': '410622', 'sttp': 'RR', 'tm': '2025-12-26 08:00:00', 'stcd': '31005650', 'rz': 245.08, 'w': 212.74, 'otq': 6.56, 'rwptn': '6', 'inq': 6.56, 'rwchrcd': None, 'inqdr': 24.0, 'msqmt': None, 'blrz': None}]
  - error: None
  - execution_time_ms: 39
  - metadata: {'query_type': 'reservoir_last', 'record_count': 1}

步骤5:   - success: True
  - data: [{'sort': None, 'lgtd': 114.1, 'lttd': 36.033055, 'stnm': '小南海', 'warn': None, 'stazt': None, 'rvnm': '安阳河', 'hnnm': '漳卫南运河', 'bsnm': '海河', 'stlc': '安阳市安阳县善应镇小南海水库管理所', 'addvcd': '410522', 'sttp': 'RR', 'tm': '2025-12-26 08:00:00', 'stcd': '31006700', 'rz': 164.39, 'w': 20.08, 'otq': None, 'rwptn': '6', 'inq': None, 'rwchrcd': None, 'inqdr': None, 'msqmt': None, 'blrz': None}]
  - error: None
  - execution_time_ms: 33
  - metadata: {'query_type': 'reservoir_last', 'record_count': 1}

步骤6: 根据卫共流域数字孪生系统的最新监测数据（截至2025年12月26日 08:00），盘石头水库和小南海水库的水位对比情况如下：

*   **盘石头水库**：当前水位为 **245.08米**。
*   **小南海水库**：当前水位为 **164.39米**。

**结论：**
**盘石头水库**的当前水位更高，比小南海水库高出 **80.69米**。

## 检索到的相关知识
无相关知识

## 输出要求
1. 根据执行结果，生成清晰、准确、专业的回答
2. 如果有数据查询结果，请整理成易于理解的格式
3. 如果执行过程中有错误，请适当说明并给出建议
4. 回答应该简洁明了，重点突出

请生成最终回答:

```

**LLM响应**:
```
根据卫共流域数字孪生系统的最新实时监测数据（截至 2025年12月26日 08:00），盘石头水库和小南海水库的水位对比情况如下：

*   **盘石头水库**：当前水位为 **245.08 米**。
*   **小南海水库**：当前水位为 **164.39 米**。

**结论：**
**盘石头水库**的当前水位更高，比小南海水库高出 **80.69 米**。
```

---


*****会话ID: 69c37726-23b1-4721-b54e-03991aaa072a | 问题: 假如未来24小时降雨300mm，进行盘石头水库洪水预报*****

## 意图分析 (Planner.analyze_intent)
**时间**: 2025-12-29 17:37:36
**提示词模板**: INTENT_ANALYSIS_PROMPT

**上下文变量**:
- context_summary: 无
- chat_history: 无
- user_message: 假如未来24小时降雨300mm，进行盘石头水库洪水预报

**完整提示词**:
```
你是卫共流域数字孪生系统的智能助手"小卫"，负责分析用户意图。

## 用户意图类别
1. general_chat - 一般对话、闲聊（如问候、感谢、闲聊、询问你的信息等）
2. knowledge_qa - 流域知识问答（关于流域概况、水利设施、防洪知识、监测站点、历时洪水、调度预案、工程治理、系统功能、专业模型等）
3. data_query - 监测数据查询（获取水情、雨情、水位、流量、视频等实时或历史监测数据）
4. flood_forecast - 洪水预报（进行洪水预报、查询预报结果、查询预警信息、查询洪水风险、获取预报边界条件等）
5. flood_simulation - 洪水预演（进行洪水预演、查询预演结果、查询预警信息、查询洪水风险、获取预演边界条件等）
6. emergency_plan - 预案生成（防洪应急预案）
7. damage_assessment - 灾损评估、避险转移等业务

## 上下文信息
对话历史摘要: 无

最近对话:
无

## 用户当前消息
假如未来24小时降雨300mm，进行盘石头水库洪水预报

## 输出要求
请分析用户意图，返回JSON格式:

**如果是 general_chat（一般对话/闲聊），请直接生成回复内容：**
{
    "intent": "general_chat",
    "confidence": 0.95,
    "direct_response": "你的友好回复内容（控制在100字以内）",
    "output_type": "text"
}

**如果是其他业务意图，返回：**
{
    "intent": "意图类别",
    "confidence": 0.95,
    "entities": {"提取的关键实体": "值"},
    "requires_data_query": true/false,
    "requires_model_call": true/false,
    "output_type": "text 或 web_page"
}

注意:
- 对于一般对话，你需要友好地回复用户，可以简要介绍自己的能力（流域介绍、工程信息查询、实时水雨情查询、洪水预报预演及应急预案生成等）
- 如果涉及图表展示（如水位趋势图、雨量分布图等），output_type应为"web_page"
- 如果只是简单文字回答，output_type应为"text"

```

**LLM响应**:
```
{'intent': 'flood_forecast', 'confidence': 0.98, 'entities': {'location': '盘石头水库', 'forecast_period': '未来24小时', 'rainfall_value': '300mm', 'task': '洪水预报'}, 'requires_data_query': False, 'requires_model_call': True, 'output_type': 'web_page'}
```

## Web页面响应合成 (Controller._generate_web_page_response)
**时间**: 2025-12-29 17:37:47
**提示词模板**: RESPONSE_GENERATION_PROMPT

**上下文变量**:
- user_message: 假如未来24小时降雨300mm，进行盘石头水库洪水预报
- intent: flood_forecast
- plan_summary: 无执行计划
- execution_results: 无执行结果
- retrieved_documents: 无相关知识

**完整提示词**:
```
你是卫共流域数字孪生系统的智能助手，负责生成最终响应。

## 用户原始问题
假如未来24小时降雨300mm，进行盘石头水库洪水预报

## 用户意图
flood_forecast

## 执行计划
无执行计划

## 执行结果
无执行结果

## 检索到的相关知识
无相关知识

## 输出要求
1. 根据执行结果，生成清晰、准确、专业的回答
2. 如果有数据查询结果，请整理成易于理解的格式
3. 如果执行过程中有错误，请适当说明并给出建议
4. 回答应该简洁明了，重点突出

请生成最终回答:

```

**LLM响应**:
```
您好！24小时降雨量达到300mm已属于**特大暴雨**级别，这对盘石头水库的防洪调度是极大的考验。

针对您的需求，作为卫共流域数字孪生系统的智能助手，我已将该情景识别为**洪水预报（flood_forecast）**任务。由于目前系统中暂无该特定极端场景的预先执行结果，我将为您说明后续的预报流程及建议：

### 1. 风险评估
*   **降雨等级**：300mm/24h 远超大暴雨标准，属于极端天气。
*   **预期影响**：盘石头水库入库流量将剧增，可能出现超标准洪水，需重点关注库水位是否会超过汛限水位或设计洪水位。

### 2. 预报执行流程
为了给您提供精准的数值结果，系统需要启动“四预”（预报、预警、预演、预案）模块进行以下模拟：
*   **产汇流计算**：基于流域下垫面数据，计算300mm降雨转化成的入库径流量。
*   **入库洪水预报**：生成入库流量过程线，预测**洪峰流量**及**峰现时间**。
*   **调洪演练**：结合当前水库水位，模拟不同泄洪方案下，水库的**最高水位**及**下泄流量**对卫河下游的影响。

### 3. 操作建议
请您在系统界面中执行以下操作以获取最终预报报表：
1.  进入**“洪水预报”**模块，手动输入该降雨情景（300mm/24h）。
2.  点击**“启动模型计算”**。
3.  系统将自动生成《盘石头水库洪水预报简报》，包含入库流量曲线、库水位演变图及下游淹没风险图。

**温馨提示**：如需系统立即代为调用特定的水文模型（如新安江模型或分布式水文模型），请确认授权，我将为您关联后台计算引擎生成详细数据。
```

---


*****会话ID: 58be3701-9401-440d-87b4-ba3eb0b7ea62 | 问题: 当前盘石头水库和小南海水库水位超汛限了吗？各自出库流量是多少？*****

## 意图分析 (Planner.analyze_intent)
**时间**: 2025-12-29 17:40:10
**提示词模板**: INTENT_ANALYSIS_PROMPT

**上下文变量**:
- context_summary: 无
- chat_history: 无
- user_message: 当前盘石头水库和小南海水库水位超汛限了吗？各自出库流量是多少？

**完整提示词**:
```
你是卫共流域数字孪生系统的智能助手"小卫"，负责分析用户意图。

## 用户意图类别
1. general_chat - 一般对话、闲聊（如问候、感谢、闲聊、询问你的信息等）
2. knowledge_qa - 流域知识问答（关于流域概况、水利设施、防洪知识、监测站点、历时洪水、调度预案、工程治理、系统功能、专业模型等）
3. data_query - 监测数据查询（获取水情、雨情、水位、流量、视频等实时或历史监测数据）
4. flood_forecast - 洪水预报（进行洪水预报、查询预报结果、查询预警信息、查询洪水风险、获取预报边界条件等）
5. flood_simulation - 洪水预演（进行洪水预演、查询预演结果、查询预警信息、查询洪水风险、获取预演边界条件等）
6. emergency_plan - 预案生成（防洪应急预案）
7. damage_assessment - 灾损评估、避险转移等业务

## 上下文信息
对话历史摘要: 无

最近对话:
无

## 用户当前消息
当前盘石头水库和小南海水库水位超汛限了吗？各自出库流量是多少？

## 输出要求
请分析用户意图，返回JSON格式:

**如果是 general_chat（一般对话/闲聊），请直接生成回复内容：**
{
    "intent": "general_chat",
    "confidence": 0.95,
    "direct_response": "你的友好回复内容（控制在100字以内）",
    "output_type": "text"
}

**如果是其他业务意图，返回：**
{
    "intent": "意图类别",
    "confidence": 0.95,
    "entities": {"提取的关键实体": "值"},
    "requires_data_query": true/false,
    "requires_model_call": true/false,
    "output_type": "text 或 web_page"
}

注意:
- 对于一般对话，你需要友好地回复用户，可以简要介绍自己的能力（流域介绍、工程信息查询、实时水雨情查询、洪水预报预演及应急预案生成等）
- 如果涉及图表展示（如水位趋势图、雨量分布图等），output_type应为"web_page"
- 如果只是简单文字回答，output_type应为"text"

```

**LLM响应**:
```
{'intent': 'data_query', 'confidence': 0.98, 'entities': {'reservoirs': ['盘石头水库', '小南海水库'], 'parameters': ['水位', '汛限水位', '出库流量'], 'time_range': '当前'}, 'requires_data_query': True, 'requires_model_call': False, 'output_type': 'web_page'}
```

## 计划生成 (Planner.generate_plan)
**时间**: 2025-12-29 17:40:44
**提示词模板**: PLAN_GENERATION_PROMPT

**上下文变量**:
- available_tools: 1. 工具名称: login_basin_system
描述: 登录卫共流域数字孪生系统，获取访问令牌(Token)。通常在需要鉴权的接口调用前执行。
类别: basin_info
参数:
  - account [string] (可选): 登录账号，可选，默认使用系统配置
  - password [string] (可选): 登录密码，可选，默认使用系统配置
  - force_refresh [boolean] (可选): 是否强制刷新Token

2. 工具名称: get_map_data
描述: 查询各类地理要素的地图数据（包含空间坐标），支持测站、水库、蓄滞洪区、分洪闸堰等类型
类别: basin_info
参数:
  - ref_table [string] (必需): 数据表名: geo_st_base(测站), geo_res_base(水库), geo_fld_stor(蓄滞洪区), geo_flo_dam(分洪闸堰)
  - filter_field [string] (可选): 查询字段名。水库使用stcd(编码)和res_name(名称)；测站、蓄滞洪区、分...(已截断)
- available_workflows: 
1. flood_forecast_workflow - 洪水预报工作流
   触发条件: 用户询问洪水预报相关问题
   
2. flood_simulation_workflow - 洪水预演工作流
   触发条件: 用户要求进行洪水模拟

3. emergency_plan_workflow - 应急预案工作流
   触发条件: 用户需要生成防洪预案

4. latest_flood_forecast_query - 最新洪水预报结果查询
   触发条件: 用户询问最新预报结果

- rag_context: 以下是相关的知识库内容：

[1] (监测设施)
水文监测站网是水文信息采集的基础设施，包括：
                - 水位站：监测河道、水库水位变化
                - 雨量站：监测降雨量和降雨强度
                - 流量站：监测河道流量
                - 水质站：监测水体水质指标
                卫共流域共有各类水文监测站点约200个，实现了重点区域全覆盖。

[2] (专业知识)
洪水预报是根据实测和预报的水文气象资料，应用水文学方法，
                对未来一定时期内的洪水过程进行预测。主要方法包括：
                1. 降雨径流预报：根据降雨量预测径流量
                2. 河道洪水演进：利用马斯京根法等计算洪水传播
                3. 水库调度：考虑水库调蓄作用优化泄洪方案
                预报精度受数据质量、模型参数等因素影响。

[3] (防洪知识)
防洪预警等级分为四级：
                ...(已截断)
- intent: data_query
- entities: {'reservoirs': ['盘石头水库', '小南海水库'], 'parameters': ['水位', '汛限水位', '出库流量'], 'time_range': '当前'}
- user_message: 当前盘石头水库和小南海水库水位超汛限了吗？各自出库流量是多少？

**完整提示词**:
```
你是卫共流域数字孪生系统的任务规划器，负责制定执行计划。

## 可用工具
1. 工具名称: login_basin_system
描述: 登录卫共流域数字孪生系统，获取访问令牌(Token)。通常在需要鉴权的接口调用前执行。
类别: basin_info
参数:
  - account [string] (可选): 登录账号，可选，默认使用系统配置
  - password [string] (可选): 登录密码，可选，默认使用系统配置
  - force_refresh [boolean] (可选): 是否强制刷新Token

2. 工具名称: get_map_data
描述: 查询各类地理要素的地图数据（包含空间坐标），支持测站、水库、蓄滞洪区、分洪闸堰等类型
类别: basin_info
参数:
  - ref_table [string] (必需): 数据表名: geo_st_base(测站), geo_res_base(水库), geo_fld_stor(蓄滞洪区), geo_flo_dam(分洪闸堰)
  - filter_field [string] (可选): 查询字段名。水库使用stcd(编码)和res_name(名称)；测站、蓄滞洪区、分洪闸堰使用code(编码)和name(名称)
  - filter_operator [string] (可选): 关系运算符: =, in, like, >, <
  - filter_value [string] (可选): 查询值，只能有一个

3. 工具名称: get_list_data
描述: 查询各类要素的列表数据（不含空间坐标），如水库防洪责任人扩展信息
类别: basin_info
参数:
  - ref_table [string] (必需): 数据表名，如geo_res_flood_ext(水库防洪责任人扩展信息)
  - filter_field [string] (可选): 查询字段名
  - filter_operator [string] (可选): 关系运算符: =, in, like
  - filter_value [string] (可选): 查询值

4. 工具名称: get_reservoir_info
描述: 查询水库的基础属性信息，包括位置、工程等级、流域面积、库容、校核洪水位等
类别: basin_info
参数:
  - stcd [string] (可选): 测站编码，可选，不传则查询所有水库

5. 工具名称: get_reservoir_flood_detail
描述: 查询单个水库的防洪特征值详情，包括校核洪水位、设计洪水位、正常蓄水位、死水位、库容等
类别: basin_info
参数:
  - stcd [string] (必需): 测站编码（必填）

6. 工具名称: get_reservoir_flood_list
描述: 获取所有水库的防洪特征值信息列表，包含各水库的校核洪水位、设计洪水位、正常蓄水位、库容等
类别: basin_info
参数:
  无参数

7. 工具名称: get_sluice_info
描述: 查询水闸的基础属性信息，包括位置、河流名称、工程规模、设计流量等
类别: basin_info
参数:
  - stcd [string] (可选): 测站编码，可选，不传则查询所有水闸

8. 工具名称: get_flood_dam_info
描述: 查询分洪闸堰的基础信息，包括位置、设计分洪流量等
类别: basin_info
参数:
  - name [string] (可选): 分洪闸堰名称，可选，支持模糊查询

9. 工具名称: get_flood_storage_area
描述: 查询蓄滞洪区的基础信息，包括面积、进洪设施、设计蓄洪库容、设计蓄洪水位等
类别: basin_info
参数:
  - name [string] (可选): 蓄滞洪区名称，可选，支持模糊查询

10. 工具名称: get_river_flood_list
描述: 获取所有河道测站的防洪特征值信息列表，包括警戒水位、保证水位、左右堤高程、实测最高水位等
类别: basin_info
参数:
  无参数

11. 工具名称: get_station_list
描述: 按测站类型查询测站的基础信息列表，包括测站编码、名称、位置、河流名称等
类别: basin_info
参数:
  - sttp [string] (必需): 测站类型: ZQ(水文站), ZZ(水位站), PP(雨量站), RR(水库站), DD(闸坝站), ZB(水位遥测站), AI(智能监测站)

12. 工具名称: get_camera_list
描述: 获取视频监控摄像头列表，包括摄像头编码、名称、关联测站、视频流地址等
类别: basin_info
参数:
  - stcd [string] (可选): 测站编码，可选，不传则查询所有摄像头

13. 工具名称: get_drone_project_list
描述: 查询无人机项目列表，获取项目ID和项目名称
类别: basin_info
参数:
  无参数

14. 工具名称: get_drone_device_list
描述: 查询无人机设备列表，获取设备序列号、名称、类型、状态等信息
类别: basin_info
参数:
  无参数

15. 工具名称: get_remote_sensing_task_list
描述: 查询遥感监测任务列表，支持洪涝水淹、洪涝监测、水利工程变形、小流域监测等任务类型
类别: basin_info
参数:
  - task_type [string] (必需): 任务类型: HHSL(洪涝水淹), HLJC(洪涝监测), SLGCBX(水利工程变形), XDMJC(小流域监测)
  - task_name [string] (可选): 任务名称，支持模糊查询
  - page [integer] (必需): 页码，从1开始
  - limit [integer] (必需): 每页条数
  - user_id [string] (必需): 用户ID

16. 工具名称: query_rain_process
描述: 根据测站编码和时间范围查询雨量历史过程数据，返回时段降水量、日降水量、累计降水量等信息
类别: hydro_monitor
参数:
  - stcd [string] (必需): 测站编码
  - search_begin_time [string] (必需): 查询开始时间，格式：yyyy-MM-dd HH:mm:ss
  - search_end_time [string] (必需): 查询结束时间，格式：yyyy-MM-dd HH:mm:ss

17. 工具名称: query_rain_statistics
描述: 根据测站编码查询雨量统计数据，返回1小时、3小时、6小时、12小时、24小时等多时段的雨量统计信息
类别: hydro_monitor
参数:
  - stcd [string] (必需): 测站编码

18. 工具名称: query_rain_sum
描述: 根据时间范围查询所有测站的雨量累计数据，返回测站编码、名称、累计降水量、测站位置等信息
类别: hydro_monitor
参数:
  - search_begin_time [string] (必需): 查询开始时间，格式：yyyy-MM-dd HH:mm:ss
  - search_end_time [string] (必需): 查询结束时间，格式：yyyy-MM-dd HH:mm:ss

19. 工具名称: query_reservoir_last
描述: 获取水库的最新实时水情数据，可以指定水库测站编码，包括库水位、蓄水量、入库流量、出库流量等信息
类别: hydro_monitor
参数:
  - stcd [string] (可选): 测站编码（可选，不传则查询所有水库）

20. 工具名称: query_reservoir_process
描述: 根据测站编码和时间范围查询水库的历史水情过程数据，返回库水位、蓄水量、入库流量、出库流量等时序数据
类别: hydro_monitor
参数:
  - stcd [string] (必需): 测站编码
  - search_begin_time [string] (必需): 查询开始时间，格式：yyyy-MM-dd HH:mm:ss
  - search_end_time [string] (必需): 查询结束时间，格式：yyyy-MM-dd HH:mm:ss

21. 工具名称: query_river_last
描述: 获取河道测站的最新实时水情数据，可以指定河道测站编码，包括水位、流量、水势、告警级别等信息
类别: hydro_monitor
参数:
  - stcd [string] (可选): 测站编码（可选，不传则查询所有河道）

22. 工具名称: query_river_process
描述: 根据测站编码和时间范围查询河道水情历史过程数据，返回水位、流量、水势等时序数据
类别: hydro_monitor
参数:
  - stcd [string] (必需): 测站编码
  - search_begin_time [string] (必需): 查询开始时间，格式：yyyy-MM-dd HH:mm:ss
  - search_end_time [string] (必需): 查询结束时间，格式：yyyy-MM-dd HH:mm:ss

23. 工具名称: query_ai_water_last
描述: 获取AI智能监测设备的最新水情数据，返回测站编码、名称、水位、数据时间等信息
类别: hydro_monitor
参数:
  无参数

24. 工具名称: query_ai_water_process
描述: 根据测站编码和时间范围查询AI智能监测设备的水情历史过程数据
类别: hydro_monitor
参数:
  - stcd [string] (必需): 测站编码
  - st [string] (必需): 开始时间，格式：yyyy-MM-dd HH:mm:ss
  - ed [string] (必需): 结束时间，格式：yyyy-MM-dd HH:mm:ss

25. 工具名称: query_ai_rain_last
描述: 获取AI智能监测设备的最新雨量数据，返回测站编码、名称、时段降水量、数据时间等信息
类别: hydro_monitor
参数:
  无参数

26. 工具名称: query_ai_rain_process
描述: 根据测站编码和时间范围查询AI智能监测设备的雨量历史过程数据
类别: hydro_monitor
参数:
  - stcd [string] (必需): 测站编码
  - st [string] (必需): 开始时间，格式：yyyy-MM-dd HH:mm:ss
  - ed [string] (必需): 结束时间，格式：yyyy-MM-dd HH:mm:ss

27. 工具名称: query_camera_preview
描述: 根据摄像头编码获取实时视频预览流地址
类别: hydro_monitor
参数:
  - code [string] (必需): 摄像头编码

28. 工具名称: query_sensor_data_process
描述: 根据传感器ID和时间范围查询传感器的历史监测数据
类别: hydro_monitor
参数:
  - sensor_id [string] (必需): 传感器ID
  - st [string] (必需): 开始时间，格式：yyyy-MM-dd HH:mm:ss
  - ed [string] (必需): 结束时间，格式：yyyy-MM-dd HH:mm:ss

29. 工具名称: query_drone_status
描述: 查询大疆无人机设备的实时状态，包括设备序列号、状态、电量、位置等信息
类别: hydro_monitor
参数:
  - device_sn [string] (必需): 无人机设备序列号

30. 工具名称: send_sms
描述: 发送告警短信通知，需要提供接收手机号码和短信内容
类别: hydro_monitor
参数:
  - phone [string] (必需): 接收短信的手机号码
  - content [string] (必需): 短信内容

31. 工具名称: model_plan_add
描述: 新增洪水预报模拟方案，设置方案名称、时间范围、业务模型等参数
类别: flood_control
参数:
  - plan_name [string] (必需): 方案名称
  - business_code [string] (必需): 业务模型编码
  - start_time [string] (必需): 开始时间，格式: yyyy-MM-dd HH:mm:ss
  - end_time [string] (必需): 结束时间，格式: yyyy-MM-dd HH:mm:ss
  - plan_desc [string] (可选): 方案描述
  - business_name [string] (可选): 业务模型名称
  - step_save_minutes [integer] (可选): 模型结果保存时间步长(分钟)
  - inherit_plan_code [string] (可选): 继承方案的编码
  - view_point [string] (可选): 相机位置
  - model_object [string] (可选): 模型参数JSON字符串

32. 工具名称: model_plan_edit
描述: 编辑已存在的洪水预报模拟方案
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码
  - plan_name [string] (可选): 方案名称
  - business_code [string] (可选): 业务模型编码
  - start_time [string] (可选): 开始时间，格式: yyyy-MM-dd HH:mm:ss
  - end_time [string] (可选): 结束时间，格式: yyyy-MM-dd HH:mm:ss
  - plan_desc [string] (可选): 方案描述
  - business_name [string] (可选): 业务模型名称
  - step_save_minutes [integer] (可选): 模型结果保存时间步长(分钟)
  - inherit_plan_code [string] (可选): 继承方案的编码
  - view_point [string] (可选): 相机位置
  - model_object [string] (可选): 模型参数JSON字符串

33. 工具名称: model_plan_delete
描述: 删除指定的洪水预报模拟方案
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

34. 工具名称: model_plan_detail
描述: 根据方案编码查看模拟方案的详细信息
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

35. 工具名称: model_plan_state
描述: 查看模拟方案的当前计算状态
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

36. 工具名称: model_plan_list_all
描述: 查询全部洪水预报模拟方案列表(不分页)，支持按方案名称、编码、状态等条件筛选
类别: flood_control
参数:
  - plan_code [string] (可选): 方案编码（精确匹配）
  - plan_name [string] (可选): 方案名称（模糊查询）
  - business_code [string] (可选): 业务模型编码
  - state [string] (可选): 计算状态：待计算/计算中/计算完成/计算失败

37. 工具名称: model_plan_calc
描述: 启动指定方案的洪水预报模型计算
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

38. 工具名称: model_plan_stop
描述: 终止正在进行的模拟方案计算
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

39. 工具名称: model_plan_progress
描述: 获取模拟方案的计算进度信息
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

40. 工具名称: model_plan_count_state
描述: 获取不同计算状态的方案数量统计
类别: flood_control
参数:
  无参数

41. 工具名称: model_plan_count_plan
描述: 获取各业务模型的模拟方案数量统计
类别: flood_control
参数:
  无参数

42. 工具名称: model_plan_auto_forecast
描述: 手动触发一次自动洪水预报计算（无需登录）
类别: flood_control
参数:
  无参数

43. 工具名称: model_basic_list_all
描述: 查询全部基础模型列表(不分页)，支持按模型名称、编码、类型等条件筛选
类别: flood_control
参数:
  - name [string] (可选): 模型名称
  - code [string] (可选): 模型编码
  - type_id [integer] (可选): 模型类型ID

44. 工具名称: model_basic_detail
描述: 根据模型ID查看基础模型的详细信息，包括模型介绍、原理、参数等
类别: flood_control
参数:
  - id [integer] (必需): 模型ID

45. 工具名称: model_basic_count
描述: 获取基础模型、模型实例、业务模型、模拟方案的数量统计
类别: flood_control
参数:
  无参数

46. 工具名称: model_instance_list_all
描述: 查询全部模型实例列表(不分页)，支持按实例名称、编码、基础模型、流域等条件筛选
类别: flood_control
参数:
  - name [string] (可选): 实例名称
  - code [string] (可选): 实例编码
  - basic_code [string] (可选): 基础模型编码
  - basin_code [string] (可选): 流域编码

47. 工具名称: model_instance_detail
描述: 根据实例ID查看模型实例的详细信息
类别: flood_control
参数:
  - id [integer] (必需): 实例ID

48. 工具名称: model_business_list_all
描述: 查询全部业务模型列表(不分页)，支持按业务模型名称、编码、类型等条件筛选
类别: flood_control
参数:
  - name [string] (可选): 业务模型名称
  - code [string] (可选): 业务模型编码
  - type_id [integer] (可选): 业务模型类型ID

49. 工具名称: model_business_add
描述: 新增业务模型，设置业务模型名称、编码、类型等参数
类别: flood_control
参数:
  - name [string] (必需): 业务模型名称
  - code [string] (必需): 业务模型编码（唯一）
  - type_id [integer] (可选): 业务模型类型ID
  - type_name [string] (可选): 业务模型类型名称
  - instance_codes [string] (可选): 模型实例编码(多个用逗号分隔)
  - view_point [string] (可选): 相机位置
  - url [string] (可选): 模型地址
  - remark [string] (可选): 备注

50. 工具名称: model_business_detail
描述: 根据业务模型编码查看业务模型的详细信息
类别: flood_control
参数:
  - code [string] (必需): 业务模型编码

51. 工具名称: forecast_rain_ecmwf_avg
描述: 获取流域平均的格网预报降雨过程(无需登录)，返回时序降雨数据
类别: flood_control
参数:
  - st [string] (必需): 开始时间，格式: yyyy-MM-dd HH:mm:ss
  - ed [string] (必需): 结束时间，格式: yyyy-MM-dd HH:mm:ss
  - business_code [string] (可选): 业务模型编码

52. 工具名称: forecast_rain_ecmwf_each
描述: 获取各子流域的格网预报降雨过程，返回按子流域编码分组的降雨时序数据
类别: flood_control
参数:
  - st [string] (必需): 开始时间，格式: yyyy-MM-dd HH:mm:ss
  - ed [string] (必需): 结束时间，格式: yyyy-MM-dd HH:mm:ss
  - business_code [string] (可选): 业务模型编码

53. 工具名称: forecast_rain_ecmwf_rect
描述: 获取矩形区域内的格网预报降雨过程，通过经纬度范围指定区域
类别: flood_control
参数:
  - st [string] (必需): 开始时间
  - ed [string] (必需): 结束时间
  - xmin [float] (必需): 矩形左边界经度
  - xmax [float] (必需): 矩形右边界经度
  - ymin [float] (必需): 矩形下边界纬度
  - ymax [float] (必需): 矩形上边界纬度

54. 工具名称: forecast_rain_ecmwf_stc
描述: 获取指定时段的ECMWF降雨分区统计信息，包括各子流域累计、平均、最大降雨量
类别: flood_control
参数:
  - st [string] (可选): 开始时间，默认当前时间
  - ed [string] (可选): 结束时间，默认开始时间后24小时

55. 工具名称: forecast_rain_ecmwf_acc
描述: 获取所有格网点指定时段的ECMWF累计降雨，返回经纬度和累计降雨值
类别: flood_control
参数:
  - st [string] (必需): 开始时间
  - ed [string] (必需): 结束时间

56. 工具名称: contour_rain_today
描述: 获取8点以后降雨等值面，返回GeoJSON格式的等值面数据
类别: flood_control
参数:
  - t [string] (可选): 时间，默认当前时间，格式: yyyy-MM-dd HH:mm:ss

57. 工具名称: contour_rain_any
描述: 生成/获取任意时段累计降雨等值面
类别: flood_control
参数:
  - st [string] (必需): 开始时间
  - ed [string] (必需): 结束时间

58. 工具名称: contour_rain_plan
描述: 生成/获取方案累计降雨等值面
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

59. 工具名称: contour_rain_proc
描述: 获取逐小时降雨等值面过程
类别: flood_control
参数:
  - t [string] (可选): 时间，默认当前时间

60. 工具名称: contour_rain_acc
描述: 获取不同时段累计降雨等值面，interval负数表示历史，正数表示未来
类别: flood_control
参数:
  - t [string] (可选): 时间，默认当前时间
  - interval [integer] (必需): 时段间隔(小时)，可选值: -1/-12/-24/-48/-72/1/12/24/48/72

61. 工具名称: contour_rain_future_img
描述: 获取未来24/48/72小时降雨等值面图片(Base64格式)
类别: flood_control
参数:
  - ind [integer] (必需): 时段索引: 0=24小时, 1=48小时, 2=72小时
  - time [string] (可选): 时间，默认当前时间

62. 工具名称: contour_rain_update
描述: 更新等值面(无需登录)
类别: flood_control
参数:
  无参数

63. 工具名称: monitor_rain_area_proc_whole
描述: 获取指定时段的流域整体面雨量过程
类别: flood_control
参数:
  - st [string] (必需): 开始时间
  - ed [string] (必需): 结束时间

64. 工具名称: monitor_rain_manual
描述: 手动更新降水监测数据(无需登录)
类别: flood_control
参数:
  - st [string] (必需): 开始时间
  - ed [string] (必需): 结束时间

65. 工具名称: model_rain_pattern_list
描述: 查询设计雨型列表
类别: flood_control
参数:
  无参数

66. 工具名称: model_rain_pattern_add
描述: 新增设计雨型
类别: flood_control
参数:
  - name [string] (必需): 雨型名称
  - type [string] (可选): 雨型类型: 0=自定义雨型, 1=设计雨型
  - json [string] (必需): 雨型过程JSON

67. 工具名称: model_rain_pattern_detail
描述: 查看设计雨型详情
类别: flood_control
参数:
  - id [integer] (必需): 雨型ID

68. 工具名称: model_typical_rain_list
描述: 分页查询典型暴雨列表
类别: flood_control
参数:
  - id [integer] (可选): 暴雨ID
  - name [string] (可选): 暴雨名称
  - page [integer] (可选): 页码，默认1
  - limit [integer] (可选): 每页条数，默认10

69. 工具名称: model_typical_rain_add
描述: 新增典型暴雨
类别: flood_control
参数:
  - name [string] (必需): 暴雨名称
  - process [array] (必需): 降雨过程数据

70. 工具名称: model_typical_rain_detail
描述: 查看典型暴雨详情
类别: flood_control
参数:
  - id [integer] (必需): 暴雨ID

71. 工具名称: model_typical_rain_add_from_history
描述: 从历史数据新增典型暴雨
类别: flood_control
参数:
  - st [string] (必需): 开始时间
  - ed [string] (必需): 结束时间
  - name [string] (必需): 暴雨名称

72. 工具名称: model_rain_area_get_by_plan
描述: 获取指定方案的各子流域降雨过程(无需登录)，返回按子流域编码分组的降雨时序数据
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

73. 工具名称: model_rain_area_get_basin_area_rain_stc
描述: 获取指定方案的全流域平均面雨量过程及统计值(无需登录)，包括累计、最大降雨量和平均值
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

74. 工具名称: model_rain_area_get_basin_area_rain_acc
描述: 获取指定方案的全流域平均面雨量过程及实时累计降雨
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

75. 工具名称: model_rain_area_get_basin_list
描述: 获取指定方案有降雨预报的流域清单
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

76. 工具名称: model_rain_area_detail
描述: 获取指定方案、指定流域的降雨过程及统计，包括累计、最大降雨量和时间
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码
  - bsn_code [string] (必需): 流域编码

77. 工具名称: model_rain_area_get_by_rsvr
描述: 获取指定方案、指定水文站的上游流域降雨过程
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码
  - stcd [string] (必需): 水文站编码

78. 工具名称: model_rain_area_forecast_rain_stc
描述: 获取自动预报方案的降雨态势，包括平均、最大降雨量和降雨等级
类别: flood_control
参数:
  - interval [integer] (必需): 时段间隔(小时)

79. 工具名称: model_rain_area_add_ecmwf
描述: 根据格网预报(ECMWF)设置方案降雨过程
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

80. 工具名称: model_rain_area_add_ecmwf_translate
描述: 根据格网预报设置方案降雨过程(可放大平移)，支持设置放大倍数和经纬度偏移量
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码
  - factor [float] (可选): 放大倍数，默认1.0
  - dlgtd [float] (可选): 经度偏移量，默认0
  - dlttd [float] (可选): 纬度偏移量，默认0

81. 工具名称: model_rain_area_add_manual
描述: 手动设置方案降雨过程，通过JSON格式指定降水量时序数据
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码
  - bsn_code [string] (可选): 子流域编码(avg表示全流域平均)
  - drp_json [string] (必需): 降水量JSON字符串，格式如：{"2025-12-16 08:00:00":3.68,"2025-12-16 09:00:00":6.2}
  - source [string] (可选): 数据来源: 0=实测, 1=预报, 2=指定, 3=无降雨

82. 工具名称: model_rain_area_add_manual_center
描述: 手动设置方案降雨过程(可设降雨中心)，支持设置多个降雨中心区域
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码
  - centers [array] (必需): 降雨中心列表，每个中心需包含drpJson(降雨过程JSON)和polyWkt(面要素WKT格式)

83. 工具名称: model_rain_area_add_bnd
描述: 从数据库导入方案降雨过程
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

84. 工具名称: flood_damage_loss_calc
描述: 根据模型编码和业务类型计算洪涝灾害造成的损失，包括受灾面积、受灾人口、受灾GDP、受灾企业数等，并返回受灾村庄和区县的GeoJSON数据
类别: damage_assess
参数:
  - code [string] (必需): 模型编码，如 model_20240829111000
  - businessType [string] (必需): 业务类型：flood_dispatch_route_wg-分洪调度路线、flood_dispatch_wg-分洪调度

85. 工具名称: hedge_placement_list
描述: 根据预案编码查询避险安置点列表，包括安置点名称、位置、联系人、容纳人数等信息
类别: damage_assess
参数:
  - planCode [string] (必需): 预案编码，如 model_20250524100026

86. 工具名称: hedge_transfer_route_list
描述: 根据预案编码查询转移路线列表，包括转移村庄、目标安置点、转移时间、联系人等信息
类别: damage_assess
参数:
  - planCode [string] (必需): 预案编码，如 model_20250524100026

87. 工具名称: model_result_outflow_delete
描述: 删除产流结果，根据方案编码和可选的流域编码删除子流域洪水计算结果
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码
  - bsn_code [string] (可选): 流域编码（可选）

88. 工具名称: model_result_outflow_get_basin_list
描述: 获取指定方案的子流域基础信息清单，返回子流域编码和名称列表
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

89. 工具名称: model_result_outflow_detail
描述: 获取指定方案、指定子流域的降雨及洪水过程结果及统计结果，包括降雨过程、洪水过程、峰值时间、累计降雨、洪峰流量等
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码
  - bsn_code [string] (必需): 流域编码

90. 工具名称: model_result_outflow_source
描述: 获取洪水来源类型：0=降雨计算、1=直接导入、2=无洪水
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

91. 工具名称: loss_plan_list
描述: 分页查询淹没分析方案列表，支持按编码、名称、状态、蓄滞洪区编码、类型等条件过滤
类别: flood_control
参数:
  - code [string] (可选): 方案编码（可选）
  - name [string] (可选): 方案名称（可选）
  - status [string] (可选): 计算状态：待计算/计算中/计算成功/计算失败（可选）
  - fsda_code [string] (可选): 蓄滞洪区编码（可选）
  - model_type [string] (可选): 类型：0=蓄滞洪区, 1=滩地（可选）
  - page [integer] (可选): 页码，默认1
  - limit [integer] (可选): 每页条数，默认10

92. 工具名称: loss_plan_add
描述: 新增淹没分析方案，用于创建新的洪水淹没分析计算方案
类别: flood_control
参数:
  - code [string] (必需): 方案编码
  - name [string] (必需): 方案名称
  - descrip [string] (可选): 方案描述（可选）
  - param_json [string] (可选): 参数JSON（可选）
  - fsda_code [string] (可选): 蓄滞洪区编码，可多个（可选）
  - fsda_name [string] (可选): 蓄滞洪区名称，可多个（可选）
  - model_type [string] (可选): 类型：0=蓄滞洪区, 1=滩地（可选）
  - save [string] (可选): 是否保存方案（可选）

93. 工具名称: loss_plan_delete
描述: 删除指定的淹没分析方案
类别: flood_control
参数:
  - code [string] (必需): 方案编码

94. 工具名称: loss_plan_calc
描述: 执行淹没分析方案计算，返回预计计算所需时间（秒）
类别: flood_control
参数:
  - code [string] (必需): 方案编码

95. 工具名称: loss_plan_detail
描述: 获取淹没分析方案详情及计算结果数据
类别: flood_control
参数:
  - code [string] (必需): 方案编码

96. 工具名称: loss_plan_gis
描述: 获取淹没分布GIS数据，返回GeoJSON格式的淹没范围和深度信息
类别: flood_control
参数:
  - path [string] (必需): 结果文件路径

97. 工具名称: loss_plan_auto
描述: 自动计算淹没分析（无需登录）
类别: flood_control
参数:
  无参数

98. 工具名称: flood_plan_list_all
描述: 查询全部防汛预案列表（不分页），支持按预案名称、文号、年度、分类等条件过滤
类别: flood_control
参数:
  - title [string] (可选): 预案名称（可选）
  - code [string] (可选): 预案文号（可选）
  - year [string] (可选): 年度（可选）
  - type1 [string] (可选): 一级分类（可选）
  - type2 [string] (可选): 二级分类（可选）

99. 工具名称: flood_plan_add
描述: 新增防汛预案（支持文件上传），用于创建新的防汛预案记录
类别: flood_control
参数:
  - title [string] (必需): 预案名称
  - code [string] (可选): 预案文号（可选）
  - year [string] (可选): 年度（可选）
  - type1 [string] (可选): 一级分类（可选）
  - type2 [string] (可选): 二级分类（可选）
  - remark [string] (可选): 备注（可选）
  - rela [string] (可选): 关联信息（可选）
  - file_id [string] (可选): 已有文件ID（可选，如不上传新文件可直接指定）

100. 工具名称: flood_plan_delete
描述: 删除指定的防汛预案
类别: flood_control
参数:
  - id [integer] (必需): 预案ID

101. 工具名称: flood_plan_detail
描述: 查看防汛预案详情，包括预案名称、文号、年度、分类、文件信息等
类别: flood_control
参数:
  - id [integer] (必需): 预案ID

102. 工具名称: flood_plan_catalog
描述: 获取防汛预案类型目录，返回一级分类及其下属二级分类的树形结构
类别: flood_control
参数:
  无参数

103. 工具名称: monitor_rsvr_now
描述: 获取水库河道实时水情（无需登录），返回水位、库容、入库流量、出库流量等实时数据
类别: flood_control
参数:
  无参数

104. 工具名称: monitor_rsvr_stc
描述: 获取水库当前形势统计，返回总数、正常数、预警数、危险数等统计信息
类别: flood_control
参数:
  无参数

105. 工具名称: monitor_rsvr_track
描述: 水雨情态势过程回溯，获取指定时段内水库水情变化过程
类别: flood_control
参数:
  - st [string] (必需): 开始时间，格式: yyyy-MM-dd HH:mm:ss
  - ed [string] (必需): 结束时间，格式: yyyy-MM-dd HH:mm:ss

106. 工具名称: monitor_rsvr_storage
描述: 水库纳蓄能力分析，返回总库容、当前蓄量、可用库容、蓄水率等信息
类别: flood_control
参数:
  - goal [integer] (必需): 目标水位或库容指标

107. 工具名称: mike_gate_all
描述: 获取闸门工情（无需登录），返回闸门状态（全开/半开/全关）、开度、开启孔数等信息
类别: flood_control
参数:
  无参数

108. 工具名称: mike_runoff
描述: 获取子流域NAM模型产流结果（无需登录），返回各子流域的产流时间序列
类别: flood_control
参数:
  - plan_code [string] (必需): 方案编码

109. 工具名称: mike_rsvr_info
描述: 获取水库基本信息（无需登录），包括水库编码、名称、汛限水位、正常水位、死水位、总库容等
类别: flood_control
参数:
  - model_instance [string] (可选): 模型实例编码（可选）

110. 工具名称: mike_control
描述: 获取水库的可控建筑物，返回泄洪洞、溢洪道等可控设施信息及最大过流能力
类别: flood_control
参数:
  - stcd [string] (必需): 水库编码

111. 工具名称: mike_hvrela
描述: 获取蓄滞洪区的库容曲线，返回水位-库容关系数据
类别: flood_control
参数:
  - code [string] (必需): 蓄滞洪区编码

112. 工具名称: mike_spec_time
描述: 获取指定时刻的水情，返回各水库测站的水位、入库流量、出库流量等数据
类别: flood_control
参数:
  - time [string] (可选): 指定时间，格式: yyyy-MM-dd HH:mm:ss（可选，默认当前时间）

113. 工具名称: mike_cal_pa
描述: 计算指定时间各子流域的前期影响雨量(Pa值)，用于洪水预报模型参数计算
类别: flood_control
参数:
  - time [string] (可选): 指定时间，格式: yyyy-MM-dd HH:mm:ss（可选，默认当前时间）

114. 工具名称: mike_fsda_struct
描述: 获取指定业务模型对应蓄滞洪区的建筑物信息，如分洪堰等
类别: flood_control
参数:
  - business_code [string] (必需): 业务模型编码

115. 工具名称: mike_fsda_set_boundary
描述: 设置蓄滞洪区进洪预演模型的边界条件，用于配置模型计算参数
类别: flood_control
参数:
  - boundary_config [object] (必需): 边界条件配置JSON对象，根据具体蓄滞洪区模型定义

116. 工具名称: auto_forcast
描述: 创建洪水自动预报模型方案并进行计算
类别: hydro_model
参数:
  无参数

117. 工具名称: create_model
描述: 手工创建模型方案，仅创建方案不设置边界条件，也不计算
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID，如'model_20230513101926'
  - fangan_name [string] (必需): 方案名称
  - start_timestr [string] (必需): 开始时间，格式如'2021/07/20 00:00:00'
  - end_timestr [string] (必需): 结束时间，格式如'2021/07/21 00:00:00'
  - fangan_desc [string] (必需): 方案描述，如'1日模拟'
  - step_saveminutes [integer] (必需): 结果保存步长(分钟)
  - base_plan_code [string] (可选): 基础方案ID，默认采用空字符串

118. 工具名称: change_model_baseinfo
描述: 修改模型方案名称、描述和保存时间步长
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - fangan_name [string] (必需): 新的模型名称
  - model_desc [string] (必需): 新的模型描述
  - step_save_minutes [integer] (必需): 保存时间步长(分钟)

119. 工具名称: del_model
描述: 删除模型方案，返回剩下的模型方案基础信息集合
类别: hydro_model
参数:
  - plan_code [string] (必需): 要删除的方案ID

120. 工具名称: run_model
描述: 计算模型，返回所需的计算时间(秒)
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID

121. 工具名称: run_model_quick
描述: 一维快速计算模型(不进行GIS结果后处理)，返回所需的计算时间(秒)
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID

122. 工具名称: stop_model
描述: 停止模型计算，返回成功信息
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID

123. 工具名称: modify_initial
描述: 修改方案的水库河道初始水位条件
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - initial_level [string] (必需): 初始水位设置。可输入'monitor'(采用监测水位)，或水位字典JSON格式如'{"站点ID1": 水位值1, "站点ID2": 水位值2}'

124. 工具名称: change_rfmodel
描述: 修改方案的各个子流域产汇流模型类型
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - rf_model [string] (可选): 产汇流模型参数JSON，格式为'{"子流域编码1": "模型编码1", "子流域编码2": "模型编码2"}'。模型编码共3种: 'nam'、'swmm5'、'xaj'。可为空对象或空字符串

125. 工具名称: change_boundry
描述: 修改方案的洪水入流边界条件，可指定为利用降雨计算洪水、直接指定子流域洪水过程、指定河道洪水过程或无洪水入流
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - bnd_type [string] (必需): 边界类型: 'rf_model'(降雨计算洪水), 'reach_inflow'(指定河道洪水), 'no_inflow'(无洪水入流), 'catchment_inflow'(指定子流域洪水)
  - bnd_value [string] (可选): 边界值JSON。当bnd_type为'reach_inflow'时，格式为'{"边界条件编码1": {"时间1": 流量1, "时间2": 流量2}}'；当bnd_type为'catchment_inflow'时，格式为'{"子流域编码1": {"时间1": 流量1}}'。其他类型不需要此参数

126. 工具名称: modify_gatestate
描述: 修改方案闸站调度设置
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - gate_dispatch [string] (必需): 调度方式。可为'monitor'(采用当前监测的闸站状态工情)、'gaterule'(采用各闸站设计调度规则)、或调度指令数组JSON格式'[["建筑物编码1",["时间1","操作类型1","闸孔数","值"]],...]'

127. 工具名称: change_reach_break
描述: 修改方案河堤溃口设置
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - break_name [string] (必需): 溃口名称
  - location [array] (必需): 溃口位置坐标 [经度, 纬度]
  - fh_width [float] (必需): 溃口宽度(米)
  - fh_minutes [integer] (必需): 溃堤时长(分钟)
  - break_condition [string] (必需): 溃决时机描述: 'max_level'(河道水位达到最高水位) 或 'set_level'(指定河道水位)
  - break_level [float] (必需): 溃决水位。当break_condition为'max_level'时可填任意值(如0)，否则填指定值

128. 工具名称: set_dispatch_target
描述: 设置方案的优化调度目标参数
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - dd_target [object] (必需): 调度目标对象，格式为'{"name": "元村", "stcd": "31004300", "max_discharge": 2500}'，包含水文站名称、水文站ID、最大允许洪峰流量
  - res_level_constraint [array] (必需): 水库调洪水位约束数组，格式为'[{"name": "双泉水库", "stcd": "31006950", "level_name": "防洪高水位", "level_value": 142.3}]'
  - other_constraint [object] (必需): 其他约束对象，格式为'{"gate": true, "reach": true, "xzhq_level": true}'，分别为闸门过流能力约束、河道过流能力约束、滞洪区滞洪水位约束

129. 工具名称: iter_cal
描述: 开始方案的优化迭代计算
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID

130. 工具名称: backcal_resdd
描述: 反向推演水库的调度方案和该调度方案下的调蓄结果。需要设置水库允许达到的最高水位，并且只针对已经完成的预报预演方案
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - res_name [string] (必需): 水库名称
  - max_level [float] (必需): 允许最高水位

131. 工具名称: set_fault_gate
描述: 设置方案的故障闸门
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - sluice_code [string] (必需): 故障水闸编码，如'QHNZ_XHKJZZ'
  - fault_desc [string] (必需): 故障信息描述，如'部分闸门无法完全关闭'
  - fault_gate_codes [array] (必需): 故障闸门编码数组，如['XHK_JZZ2', 'XHK_JZZ4']
  - gate_openings [array] (必需): 水闸各闸门开度数组，如[0, 0.5, 0, 0.2, 0]

132. 工具名称: get_sampleline
描述: 获取GIS样板线，为geojson格式的河道分段线要素，用于在地图区分色动态渲染过程结果，如流量、流速等
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

133. 工具名称: get_reachinfo
描述: 获取河道基本信息，包括河道名称、编码、起止桩号及长度等信息
类别: hydro_model
参数:
  - model_instance [string] (必需): 模型实例名称字符串

134. 工具名称: get_gatestate
描述: 获取全流域里各闸站建筑最新状态监测信息，包括闸门状态、开孔数、开度、更新时间
类别: hydro_model
参数:
  - business_code [string] (必需): 业务编码字符串

135. 工具名称: get_sectiondata
描述: 根据断面STCD和桩号，获取河道断面原始测量数据。当断面为水文站点或闸站时，第1个参数为该站点STCD，第2个为空字符串；否则第1个参数为河道编码，第2个为桩号
类别: hydro_model
参数:
  - stcd_or_reach_code [string] (必需): 站点STCD(如'31004300')或河道编码(如'GQ')
  - chainage [string] (必需): 桩号。当第1个参数为站点STCD时，填空字符串''；否则填具体桩号值(如'155000')

136. 工具名称: get_sectiondata_frompoint
描述: 根据坐标点，获取河道断面原始测量数据
类别: hydro_model
参数:
  - longitude [string] (必需): 经度，如'114.15169'
  - latitude [string] (必需): 纬度，如'35.483368'

137. 工具名称: get_reachsection_location
描述: 根据河道断面桩号，获取该河道断面中心点的经纬度坐标位置信息
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - section_location [array] (必需): 断面位置信息数组，格式如[["GQ",53263],["GQ",43263],["WH",13263]]，包含河道编码和桩号

138. 工具名称: get_station_info
描述: 获取河道上各大中型水库、河道水文站点、河道控制闸站的基本信息和监测水情信息，包括站点stcd、所在河道和桩号、控制流域面积、水位流量等监测水情信息等
类别: hydro_model
参数:
  无参数

139. 工具名称: get_strddrule_info
描述: 获取水库、河道闸站等所有洪水控制建筑的规则调度信息
类别: hydro_model
参数:
  - business_code [string] (必需): 业务编码字符串

140. 工具名称: get_control_strs
描述: 根据业务编码和站点STCD获取关联的洪水控制建筑物，如水库的各个溢流堰和泄洪洞，蓄滞洪区的各个进洪分洪闸堰
类别: hydro_model
参数:
  - business_code [string] (必需): 业务编码
  - obj_stcd [string] (必需): 对象站点编码

141. 工具名称: get_now_waterinfo
描述: 获取所有水库、河道闸站、水文站点当前最新水情信息。如果业务编码字符串为空字符串，则获取所有水库闸站和水文站点的当前水情，否则是业务模型相关的
类别: hydro_model
参数:
  - business_code [string] (可选): 业务编码字符串，可为空字符串

142. 工具名称: get_design_flood
描述: 获取和业务模型相关的各河道不同量级设计洪水过程，如50年一遇设计洪水过程
类别: hydro_model
参数:
  - business_code [string] (必需): 业务编码字符串

143. 工具名称: get_nsbd_sectioninfo
描述: 获取流域范围内，各河道与南水北调交叉断面的基本信息，包括交叉断面位置、设计水位、设计流量、校核流量、堤顶高程等
类别: hydro_model
参数:
  无参数

144. 工具名称: get_business_view
描述: 获取业务模型的默认初始三维场景相机姿态信息，包括相机位置坐标、朝向和俯仰角
类别: hydro_model
参数:
  - business_model [string] (必需): 业务模型字符串

145. 工具名称: get_rfmodel
描述: 获取方案的产汇流模型类型，返回各子流域采用的产汇流模型编码（共3种：nam、swmm5、xaj）
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

146. 工具名称: get_reach_break
描述: 获取方案河堤溃口设置信息，包括溃口编码、名称、位置、溃口宽度、溃堤时长、溃决水位、溃口底高程、开始溃口时间等
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

147. 工具名称: get_faultgate_baseinfo
描述: 获取故障水闸的闸门基本信息，根据业务编码获取，一个业务编码对应一个故障水闸。返回建筑物编码、名称及各闸门的编码、名称、闸底高程、闸门高度、经纬度坐标等信息
类别: hydro_model
参数:
  - business_code [string] (必需): 业务编码字符串

148. 工具名称: get_fault_gate
描述: 获取方案的故障闸门信息，包括故障水闸名称、故障描述、各闸门最大开度和当前开度、故障闸门名称及经纬度
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

149. 工具名称: get_ddinfo
描述: 获取模型方案所有可控建筑物的调度信息，包括建筑物编码、序号、名称、类型、所在河道及闸门调度过程
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

150. 工具名称: get_initial_waterlevel
描述: 获取模型方案的初始水情信息，包括各水库和河道站点的序号、名称、初始水位、水位来源、stcd编码等
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

151. 工具名称: get_bndinfo
描述: 获取模型方案的边界条件信息，包括边界条件类型描述（如'降雨计算洪水'）和边界条件值（各子流域的流量过程）
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

152. 工具名称: get_dispatch_target
描述: 获取方案的优化调度目标设置信息，包括方案ID、调度目标（站点名称、stcd、最大流量）、各水库约束水位及其他约束条件
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

153. 工具名称: get_models
描述: 获取已有所有模型方案信息，包括方案名称、描述、业务模型编码、起止时间、状态、进度等12个属性
类别: hydro_model
参数:
  - model_instance [string] (可选): 模型实例名称字符串，默认为'wg_mike11'

154. 工具名称: get_dispatch_plan
描述: 获取方案主要控制闸站的简短调度指令，包含水库、河道闸站、蓄滞洪区3种类型的各控制闸站的调度信息
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

155. 工具名称: get_tjdata_result
描述: 获取方案的结果数据，包含水库、河道断面、蓄滞洪区的洪水计算结果以及结果概述、河道风险，此外还可能包含调度方案结果
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

156. 工具名称: get_gisgc_polygon_result
描述: 获取方案某时刻河道水面GIS面要素结果，为geojson格式的带Z值的三维水面要素，用于在三维场景中绘制三维水面
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - now_time [string] (必需): 时间字符串，如'2021/07/20 08:00:00'

157. 工具名称: get_sampleline_data_result
描述: 获取方案的GIS过程线的全过程属性结果，用于在地图区分色动态渲染过程结果，如流量、流速等
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - gis_restype [string] (必需): 结果数据类型: 'Waterlevel'(水位), 'Speed'(流速), 'Waterh'(水深), 'Discharge'(流量)

158. 工具名称: get_gistj_result
描述: 获取方案的GIS统计线结果，为geojson格式的河道分段线要素，用于在地图区分色渲染全过程最大流量、流速等分布结果
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

159. 工具名称: get_gistj_polygon_result
描述: 获取方案的GIS统计面结果(淹没面)，为geojson格式的二维面要素，用于在地图中分水渲染淹没区水深分布
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

160. 工具名称: get_point_result
描述: 查询方案河道上某点的水位流量等结果，用于在地图中点击查询某位置结果信息。如果时间为空字符串，则返回时间序列
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - now_time [string] (必需): 时间字符串，如'2021/07/20 08:00:00'。如果为空字符串''，则返回时间序列
  - jd [string] (必需): 经度
  - wd [string] (必需): 纬度

161. 工具名称: get_zp_result
描述: 获取方案某类结果的顺河道纵剖面数据，用于前端页面纵剖图绘制
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - res_type [string] (必需): 结果数据类型: 'swzd_result'(水位纵断), 'qzd_result'(流量纵断), 'vzd_result'(流速纵断)

162. 工具名称: get_reachsections
描述: 获取方案有水位结果的河道断面桩号清单，包括各河道基本信息和各河道有水位结果的断面桩号
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

163. 工具名称: get_sectionres
描述: 获取方案单一河道断面的水位流量过程
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - reach_name [string] (必需): 河道名称(编码)
  - chainage [number] (必需): 断面桩号

164. 工具名称: get_sectionlist_res
描述: 获取方案多个河道断面的水位流量过程
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - sections [array] (必需): 断面数组，格式为[{'reach':'河道编码1','chainages':[桩号1,桩号2]},{'reach':'河道编码2','chainages':[桩号1]}]

165. 工具名称: get_catchment_discharges
描述: 获取方案多个子流域的产汇流模型流量过程
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - sub_catchment_q [object] (必需): 子流域属性对象，属性和值均为子流域编码，如{'jyh_czyx':'jyh_czyx','jlh_jgsk':'jlh_jgsk'}

166. 工具名称: get_gateres
描述: 获取方案某闸门的水力要素结果，包括过闸流量、上下游水位过程、流速过程、水头差等
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID
  - gate_name [string] (必需): 闸门编码

167. 工具名称: get_atreach
描述: 根据方案ID获取该方案的特殊河道断面信息，包括河道ID和桩号
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

168. 工具名称: get_risk_warning
描述: 获取方案的风险预警信息，包含水库风险预警、河道风险预警、蓄滞洪区进洪风险预警、降雨预警、南水北调交叉断面风险预警、山洪风险预警
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

169. 工具名称: get_history_autoforcast_list
描述: 获取历史洪水自动预报方案信息清单，包含方案ID、预报起止时间和本场次降雨总降雨量
类别: hydro_model
参数:
  无参数

170. 工具名称: del_history_autoforcast
描述: 删除某场历史自动预报方案
类别: hydro_model
参数:
  - history_plan_id [string] (必需): 历史预报方案ID字符串

171. 工具名称: get_rain_flood_list
描述: 获取预演场次洪水信息列表，所有预演方案均关联有一场场次洪水，一场场次洪水可能对应多个预演方案，但只有一个推荐方案
类别: hydro_model
参数:
  无参数

172. 工具名称: get_rainflood_plan_list
描述: 获取某场次洪水的预演方案清单，包含方案名称、描述、业务模型、起止时间、状态等信息
类别: hydro_model
参数:
  - flood_id [string] (必需): 场次洪水ID字符串

173. 工具名称: change_rainflood_recomplan
描述: 修改某场次洪水的推荐预演方案
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

174. 工具名称: important_inspect
描述: 获取预演方案的工程重点巡查区域信息，即通过方案预演后得到的工程风险区域作为重点巡查区域，包含水库、河道、蓄滞洪区的巡查信息
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串

175. 工具名称: get_history_autoforcast_res
描述: 获取历史洪水自动预报结果，结果与get_tjdata_result接口返回结果相同
类别: hydro_model
参数:
  - history_plan_id [string] (必需): 历史预报ID字符串

176. 工具名称: get_mountain_forecast_flood
描述: 获取山区预报信息，包括山洪区域名称、村庄名称、经纬度、被淹时间、风险等级等
类别: hydro_model
参数:
  - plan_code [string] (必需): 方案ID字符串


## 可用工作流

1. flood_forecast_workflow - 洪水预报工作流
   触发条件: 用户询问洪水预报相关问题
   
2. flood_simulation_workflow - 洪水预演工作流
   触发条件: 用户要求进行洪水模拟

3. emergency_plan_workflow - 应急预案工作流
   触发条件: 用户需要生成防洪预案

4. latest_flood_forecast_query - 最新洪水预报结果查询
   触发条件: 用户询问最新预报结果


## 相关知识和业务流程参考
以下是相关的知识库内容：

[1] (监测设施)
水文监测站网是水文信息采集的基础设施，包括：
                - 水位站：监测河道、水库水位变化
                - 雨量站：监测降雨量和降雨强度
                - 流量站：监测河道流量
                - 水质站：监测水体水质指标
                卫共流域共有各类水文监测站点约200个，实现了重点区域全覆盖。

[2] (专业知识)
洪水预报是根据实测和预报的水文气象资料，应用水文学方法，
                对未来一定时期内的洪水过程进行预测。主要方法包括：
                1. 降雨径流预报：根据降雨量预测径流量
                2. 河道洪水演进：利用马斯京根法等计算洪水传播
                3. 水库调度：考虑水库调蓄作用优化泄洪方案
                预报精度受数据质量、模型参数等因素影响。

[3] (防洪知识)
防洪预警等级分为四级：
                - 蓝色预警（IV级）：可能发生一般洪水
                - 黄色预警（III级）：可能发生较大洪水
                - 橙色预警（II级）：可能发生大洪水
                - 红色预警（I级）：可能发生特大洪水
                各级预警对应不同的应急响应措施和人员转移要求。


## 用户意图
意图类别: data_query
提取实体: {'reservoirs': ['盘石头水库', '小南海水库'], 'parameters': ['水位', '汛限水位', '出库流量'], 'time_range': '当前'}

## 用户消息
当前盘石头水库和小南海水库水位超汛限了吗？各自出库流量是多少？

## 输出要求
请生成执行计划，返回JSON格式:
{
    "steps": [
        {
            "step_id": 1,
            "description": "步骤描述",
            "tool_name": "工具名称（如果需要）",
            "tool_args": {"参数": "值"},
            "dependencies": [],
            "is_async": false
        }
    ],
    "estimated_time_seconds": 30,
    "output_type": "text 或 web_page"
}

规划原则:
1. 步骤应该清晰、可执行
2. 正确设置步骤间的依赖关系
3. 耗时操作（如模型调用）应标记为异步
4. 最后一步不需要指定工具，系统会自动生成响应
5. 只使用可用工具列表中存在的工具名称，不要使用不存在的工具如"generate_response"
6. 参考"相关知识和业务流程参考"中的信息，优化执行计划的步骤和工具选择

```

**LLM响应**:
```
{'steps': [{'step_id': 1, 'description': '登录卫共流域数字孪生系统以获取访问令牌', 'tool_name': 'login_basin_system', 'tool_args': {}, 'dependencies': [], 'is_async': False}, {'step_id': 2, 'description': '查询盘石头水库的测站编码(stcd)', 'tool_name': 'get_map_data', 'tool_args': {'ref_table': 'geo_res_base', 'filter_field': 'res_name', 'filter_operator': '=', 'filter_value': '盘石头水库'}, 'dependencies': [1], 'is_async': False}, {'step_id': 3, 'description': '查询小南海水库的测站编码(stcd)', 'tool_name': 'get_map_data', 'tool_args': {'ref_table': 'geo_res_base', 'filter_field': 'res_name', 'filter_operator': '=', 'filter_value': '小南海水库'}, 'dependencies': [1], 'is_async': False}, {'step_id': 4, 'description': '获取盘石头水库的最新实时水情数据（水位、出库流量）', 'tool_name': 'query_reservoir_last', 'tool_args': {'stcd': '$$2.data[0].stcd$$'}, 'dependencies': [2], 'is_async': False}, {'step_id': 5, 'description': '获取小南海水库的最新实时水情数据（水位、出库流量）', 'tool_name': 'query_reservoir_last', 'tool_args': {'stcd': '$$3.data[0].stcd$$'}, 'dependencies': [3], 'is_async': Fa...(已截断)
```

## 任务执行(LLM) (Executor._execute_with_llm)
**时间**: 2025-12-29 17:41:07
**提示词模板**: EXECUTOR_LLM_PROMPT

**上下文变量**:
- task_description: 对比实时水位与汛限水位，并汇总出库流量信息进行回答
- user_message: 当前盘石头水库和小南海水库水位超汛限了吗？各自出库流量是多少？
- execution_results: 步骤1 (成功): {'success': False, 'data': None, 'error': "HTTP请求错误: Server error '502 Bad Gateway' for url 'http://10.20.2.153/api/basin/loginApi'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/502", 'execution_time_ms': 2532, 'metadata': None}步骤2 (成功): {'success': False, 'data': None, 'error': "HTTP请求错误: Server error '502 Bad Gateway' for url 'http://10.20.2.153/api/basin/map/dataSource/table/map?refTable=geo_res_base&where%5B0%5D%5Bfiled%5D=res_name&where%5B0%...(已截断)
- retrieved_documents: 无

**完整提示词**:
```
你是卫共流域数字孪生系统的智能助手。

## 任务
对比实时水位与汛限水位，并汇总出库流量信息进行回答

## 用户原始消息
当前盘石头水库和小南海水库水位超汛限了吗？各自出库流量是多少？

## 已有执行结果
步骤1 (成功): {'success': False, 'data': None, 'error': "HTTP请求错误: Server error '502 Bad Gateway' for url 'http://10.20.2.153/api/basin/loginApi'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/502", 'execution_time_ms': 2532, 'metadata': None}步骤2 (成功): {'success': False, 'data': None, 'error': "HTTP请求错误: Server error '502 Bad Gateway' for url 'http://10.20.2.153/api/basin/map/dataSource/table/map?refTable=geo_res_base&where%5B0%5D%5Bfiled%5D=res_name&where%5B0%5D%5Brela%5D=%3D&where%5B0%5D%5Bvalue%5D=%27%E7%9B%98%E7%9F%B3%E5%A4%B4%E6%B0%B4%E5%BA%93%27'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/502", 'execution_time_ms': 5388, 'metadata': None}步骤3 (成功): {'success': False, 'data': None, 'error': "HTTP请求错误: Server error '502 Bad Gateway' for url 'http://10.20.2.153/api/basin/map/dataSource/table/map?refTable=geo_res_base&where%5B0%5D%5Bfiled%5D=res_name&where%5B0%5D%5Brela%5D=%3D&where%5B0%5D%5Bvalue%5D=%27%E5%B0%8F%E5%8D%97%E6%B5%B7%E6%B0%B4%E5%BA%93%27'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/502", 'execution_time_ms': 6027, 'metadata': None}步骤4 (成功): {'success': False, 'data': None, 'error': '参数 stcd 应为字符串类型', 'execution_time_ms': None, 'metadata': None}步骤5 (成功): {'success': False, 'data': None, 'error': '参数 stcd 应为字符串类型', 'execution_time_ms': None, 'metadata': None}步骤6 (成功): {'success': False, 'data': None, 'error': "Server error '502 Bad Gateway' for url 'http://10.20.2.153:8089/modelPlatf/model/mike/rsvrInfo'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/502", 'execution_time_ms': 2885, 'metadata': None}

## 检索到的知识
无

请根据以上信息完成任务，给出清晰、准确的回答。

```

**LLM响应**:
```
您好！我是卫共流域数字孪生系统的智能助手。

针对您查询**盘石头水库**和**小南海水库**实时水位及出库流量的需求，我很抱歉地通知您：

目前系统在尝试调取实时监测数据时遇到了技术故障（服务器返回 **502 Bad Gateway** 错误），导致无法获取最新的水情数据。

**当前状况如下：**
1. **数据获取失败**：由于后端服务暂不可用，我暂时无法获取这两个水库的当前水位、汛限水位以及实时出库流量。
2. **对比分析无法进行**：在缺失实时数据的情况下，无法为您准确判断水位是否超汛限。

**建议：**
* 请稍后再试，系统管理人员可能正在对服务器进行维护或修复。
* 如果您有紧急查阅需求，建议通过其他官方防汛调度渠道或联系系统管理员核实当前水情。

一旦系统恢复正常，我将能立即为您提供精准的对比分析和流量汇总信息。
```

## Web页面响应合成 (Controller._generate_web_page_response)
**时间**: 2025-12-29 17:41:14
**提示词模板**: RESPONSE_GENERATION_PROMPT

**上下文变量**:
- user_message: 当前盘石头水库和小南海水库水位超汛限了吗？各自出库流量是多少？
- intent: data_query
- plan_summary: 1. 登录卫共流域数字孪生系统以获取访问令牌 [completed]
2. 查询盘石头水库的测站编码(stcd) [completed]
3. 查询小南海水库的测站编码(stcd) [completed]
4. 获取盘石头水库的最新实时水情数据（水位、出库流量） [completed]
5. 获取小南海水库的最新实时水情数据（水位、出库流量） [completed]
6. 查询所有水库的汛限水位等基本信息 [completed]
7. 对比实时水位与汛限水位，并汇总出库流量信息进行回答 [completed]
- execution_results: 步骤1:   - success: False
  - data: None
  - error: HTTP请求错误: Server error '502 Bad Gateway' for url 'http://10.20.2.153/api/basin/loginApi'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/502
  - execution_time_ms: 2532
  - metadata: None

步骤2:   - success: False
  - data: None
  - error: HTTP请求错误: Server error '502 Bad Gateway' for url 'http://10.20.2.153/api/basin/map/dataSource/table/map?refTable=geo_res_base&where%5B0%5D%5Bfiled%5D=res_name&where%5B0%5D%5B...(已截断)
- retrieved_documents: 无相关知识

**完整提示词**:
```
你是卫共流域数字孪生系统的智能助手，负责生成最终响应。

## 用户原始问题
当前盘石头水库和小南海水库水位超汛限了吗？各自出库流量是多少？

## 用户意图
data_query

## 执行计划
1. 登录卫共流域数字孪生系统以获取访问令牌 [completed]
2. 查询盘石头水库的测站编码(stcd) [completed]
3. 查询小南海水库的测站编码(stcd) [completed]
4. 获取盘石头水库的最新实时水情数据（水位、出库流量） [completed]
5. 获取小南海水库的最新实时水情数据（水位、出库流量） [completed]
6. 查询所有水库的汛限水位等基本信息 [completed]
7. 对比实时水位与汛限水位，并汇总出库流量信息进行回答 [completed]

## 执行结果
步骤1:   - success: False
  - data: None
  - error: HTTP请求错误: Server error '502 Bad Gateway' for url 'http://10.20.2.153/api/basin/loginApi'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/502
  - execution_time_ms: 2532
  - metadata: None

步骤2:   - success: False
  - data: None
  - error: HTTP请求错误: Server error '502 Bad Gateway' for url 'http://10.20.2.153/api/basin/map/dataSource/table/map?refTable=geo_res_base&where%5B0%5D%5Bfiled%5D=res_name&where%5B0%5D%5Brela%5D=%3D&where%5B0%5D%5Bvalue%5D=%27%E7%9B%98%E7%9F%B3%E5%A4%B4%E6%B0%B4%E5%BA%93%27'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/502
  - execution_time_ms: 5388
  - metadata: None

步骤3:   - success: False
  - data: None
  - error: HTTP请求错误: Server error '502 Bad Gateway' for url 'http://10.20.2.153/api/basin/map/dataSource/table/map?refTable=geo_res_base&where%5B0%5D%5Bfiled%5D=res_name&where%5B0%5D%5Brela%5D=%3D&where%5B0%5D%5Bvalue%5D=%27%E5%B0%8F%E5%8D%97%E6%B5%B7%E6%B0%B4%E5%BA%93%27'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/502
  - execution_time_ms: 6027
  - metadata: None

步骤4:   - success: False
  - data: None
  - error: 参数 stcd 应为字符串类型
  - execution_time_ms: None
  - metadata: None

步骤5:   - success: False
  - data: None
  - error: 参数 stcd 应为字符串类型
  - execution_time_ms: None
  - metadata: None

步骤6:   - success: False
  - data: None
  - error: Server error '502 Bad Gateway' for url 'http://10.20.2.153:8089/modelPlatf/model/mike/rsvrInfo'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/502
  - execution_time_ms: 2885
  - metadata: None

步骤7: 您好！我是卫共流域数字孪生系统的智能助手。

针对您查询**盘石头水库**和**小南海水库**实时水位及出库流量的需求，我很抱歉地通知您：

目前系统在尝试调取实时监测数据时遇到了技术故障（服务器返回 **502 Bad Gateway** 错误），导致无法获取最新的水情数据。

**当前状况如下：**
1. **数据获取失败**：由于后端服务暂不可用，我暂时无法获取这两个水库的当前水位、汛限水位以及实时出库流量。
2. **对比分析无法进行**：在缺失实时数据的情况下，无法为您准确判断水位是否超汛限。

**建议：**
* 请稍后再试，系统管理人员可能正在对服务器进行维护或修复。
* 如果您有紧急查阅需求，建议通过其他官方防汛调度渠道或联系系统管理员核实当前水情。

一旦系统恢复正常，我将能立即为您提供精准的对比分析和流量汇总信息。

## 检索到的相关知识
无相关知识

## 输出要求
1. 根据执行结果，生成清晰、准确、专业的回答
2. 如果有数据查询结果，请整理成易于理解的格式
3. 如果执行过程中有错误，请适当说明并给出建议
4. 回答应该简洁明了，重点突出

请生成最终回答:

```

**LLM响应**:
```
您好！我是卫共流域数字孪生系统的智能助手。

针对您查询**盘石头水库**和**小南海水库**实时水位及出库流量的需求，由于系统目前出现技术故障，暂时无法获取实时监测数据。

**当前情况说明：**
*   **系统异常**：在尝试调用水情接口获取数据时，服务器返回了 **502 Bad Gateway** 错误，导致无法访问后端数据库。
*   **数据缺失**：受此影响，我暂时无法获取这两个水库的**当前实时水位**、**汛限水位**以及**实时出库流量**。
*   **无法判断**：在缺乏实时数据和汛限标准的情况下，目前无法为您准确判断水位是否超汛限。

**建议：**
1.  **稍后重试**：系统管理人员可能正在对服务器进行维护或修复，建议您过段时间再次尝试查询。
2.  **紧急核实**：如果您有紧急防汛调度需求，建议通过其他官方防汛通讯渠道或直接联系系统管理员获取当前最新的水情信息。

一旦系统恢复正常，我将立即为您提供精准的对比分析和流量数据。给您带来的不便敬请谅解。
```

---


*****会话ID: a589e237-3e2c-4811-b611-d3673a647a8d | 问题: 当前盘石头水库和小南海水库水位超汛限了吗？各自出库流量是多少？*****

## 意图分析 (Planner.analyze_intent)
**时间**: 2025-12-29 17:42:52
**提示词模板**: INTENT_ANALYSIS_PROMPT

**上下文变量**:
- context_summary: 无
- chat_history: 无
- user_message: 当前盘石头水库和小南海水库水位超汛限了吗？各自出库流量是多少？

**完整提示词**:
```
你是卫共流域数字孪生系统的智能助手"小卫"，负责分析用户意图。

## 用户意图类别
1. general_chat - 一般对话、闲聊（如问候、感谢、闲聊、询问你的信息等）
2. knowledge_qa - 流域知识问答（关于流域概况、水利设施、防洪知识、监测站点、历时洪水、调度预案、工程治理、系统功能、专业模型等）
3. data_query - 监测数据查询（获取水情、雨情、水位、流量、视频等实时或历史监测数据）
4. flood_forecast - 洪水预报（进行洪水预报、查询预报结果、查询预警信息、查询洪水风险、获取预报边界条件等）
5. flood_simulation - 洪水预演（进行洪水预演、查询预演结果、查询预警信息、查询洪水风险、获取预演边界条件等）
6. emergency_plan - 预案生成（防洪应急预案）
7. damage_assessment - 灾损评估、避险转移等业务

## 上下文信息
对话历史摘要: 无

最近对话:
无

## 用户当前消息
当前盘石头水库和小南海水库水位超汛限了吗？各自出库流量是多少？

## 输出要求
请分析用户意图，返回JSON格式:

**如果是 general_chat（一般对话/闲聊），请直接生成回复内容：**
{
    "intent": "general_chat",
    "confidence": 0.95,
    "direct_response": "你的友好回复内容（控制在100字以内）",
    "output_type": "text"
}

**如果是其他业务意图，返回：**
{
    "intent": "意图类别",
    "confidence": 0.95,
    "entities": {"提取的关键实体": "值"},
    "requires_data_query": true/false,
    "requires_model_call": true/false,
    "output_type": "text 或 web_page"
}

注意:
- 对于一般对话，你需要友好地回复用户，可以简要介绍自己的能力（流域介绍、工程信息查询、实时水雨情查询、洪水预报预演及应急预案生成等）
- 如果涉及图表展示（如水位趋势图、雨量分布图等），output_type应为"web_page"
- 如果只是简单文字回答，output_type应为"text"

```

**LLM响应**:
```
{'intent': 'data_query', 'confidence': 0.98, 'entities': {'reservoirs': ['盘石头水库', '小南海水库'], 'parameters': ['水位', '汛限水位', '出库流量'], 'time': '当前'}, 'requires_data_query': True, 'requires_model_call': False, 'output_type': 'web_page'}
```

