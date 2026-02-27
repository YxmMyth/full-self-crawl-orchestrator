-- Migration: 002_add_task_tables.sql
-- Description: Add tables for task persistence and history tracking

-- 主任务表
CREATE TABLE IF NOT EXISTS research_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) UNIQUE NOT NULL,
    user_query TEXT NOT NULL,
    refined_requirement JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    candidate_sites JSONB DEFAULT '[]',
    successful_sites INTEGER DEFAULT 0,
    failed_sites INTEGER DEFAULT 0,
    total_duration_sec INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 站点结果表
CREATE TABLE IF NOT EXISTS site_results (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL REFERENCES research_tasks(task_id) ON DELETE CASCADE,
    site_url VARCHAR(500) NOT NULL,
    site_name VARCHAR(200),
    quality_score NUMERIC(5,2),
    total_records INTEGER DEFAULT 0,
    sample_records JSONB DEFAULT '[]',
    duration_sec INTEGER DEFAULT 0,
    strategy_used VARCHAR(100),
    difficulty VARCHAR(50),
    anti_bot JSONB DEFAULT '[]',
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(task_id, site_url)
);

-- 样本数据表
CREATE TABLE IF NOT EXISTS sample_records (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL REFERENCES research_tasks(task_id) ON DELETE CASCADE,
    site_url VARCHAR(500) NOT NULL,
    record_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_research_tasks_status ON research_tasks(status);
CREATE INDEX IF NOT EXISTS idx_research_tasks_created_at ON research_tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_tasks_task_id ON research_tasks(task_id);

CREATE INDEX IF NOT EXISTS idx_site_results_task_id ON site_results(task_id);
CREATE INDEX IF NOT EXISTS idx_site_results_quality_score ON site_results(quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_site_results_status ON site_results(status);

CREATE INDEX IF NOT EXISTS idx_sample_records_task_id ON sample_records(task_id);
CREATE INDEX IF NOT EXISTS idx_sample_records_site_url ON sample_records(site_url);

-- 更新时间戳的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为表添加更新时间戳触发器
DROP TRIGGER IF EXISTS update_research_tasks_updated_at ON research_tasks;
CREATE TRIGGER update_research_tasks_updated_at
    BEFORE UPDATE ON research_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_site_results_updated_at ON site_results;
CREATE TRIGGER update_site_results_updated_at
    BEFORE UPDATE ON site_results
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 添加注释
COMMENT ON TABLE research_tasks IS '数据源调研任务主表';
COMMENT ON TABLE site_results IS '站点探测结果表';
COMMENT ON TABLE sample_records IS '采集样本数据表';

COMMENT ON COLUMN research_tasks.task_id IS '任务唯一标识';
COMMENT ON COLUMN research_tasks.user_query IS '用户原始查询';
COMMENT ON COLUMN research_tasks.refined_requirement IS '精确化后的需求（JSON格式）';
COMMENT ON COLUMN research_tasks.status IS '任务状态: pending/running/completed/failed';
COMMENT ON COLUMN research_tasks.candidate_sites IS '候选站点列表（JSON格式）';

COMMENT ON COLUMN site_results.task_id IS '关联的任务ID';
COMMENT ON COLUMN site_results.site_url IS '站点URL';
COMMENT ON COLUMN site_results.quality_score IS '质量评分(0-100)';
COMMENT ON COLUMN site_results.sample_records IS '样本记录（JSON格式）';
COMMENT ON COLUMN site_results.status IS '探测状态: pending/success/failed';
